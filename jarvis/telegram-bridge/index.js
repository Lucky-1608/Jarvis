process.env.NTBA_FIX_319 = 1;
process.env.NTBA_FIX_350 = 1;
require('dotenv').config({ path: '../../.env' });
const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');
const http = require('http');

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const OWNER_ID = process.env.TELEGRAM_OWNER_ID;

if (!BOT_TOKEN || BOT_TOKEN === 'YOUR_BOT_TOKEN_HERE') {
    console.error("ERROR: TELEGRAM_BOT_TOKEN is not set correctly in the .env file.");
    console.error("Please get a token from @BotFather on Telegram and add it to ../../.env");
    process.exit(1);
}

if (!OWNER_ID || OWNER_ID === 'YOUR_OWNER_ID_HERE') {
    console.error("ERROR: TELEGRAM_OWNER_ID is not set correctly in the .env file.");
    console.error("Please get your numeric user ID from @userinfobot on Telegram and add it to ../../.env");
    process.exit(1);
}

const localPort = process.env.PORT || 8000;
const JARVIS_BACKEND_URL = (process.env.JARVIS_BACKEND_URL || `http://127.0.0.1:${localPort}`).replace(/\/+$/, '');
const JARVIS_EVENT_URL = `${JARVIS_BACKEND_URL}/api/telegram/event`;

let globalBot = null;

async function sendStatus(status, data = null, retries = 15) {
    for (let i = 0; i < retries; i++) {
        try {
            await axios.post(JARVIS_EVENT_URL, {
                type: status,
                data: data
            }, {
                headers: { 'X-API-Key': process.env.JARVIS_SECRET_KEY || 'JARVIS_DEV_KEY' }
            });
            return;
        } catch (err) {
            console.error(`Could not send status to Jarvis (attempt ${i + 1}/${retries}):`, err.message);
            if (i < retries - 1) {
                await new Promise(resolve => setTimeout(resolve, 2000));
            }
        }
    }
}

/**
 * Converts markdown tables to clean, readable bullet points for chat
 */
function convertTablesToReadableFormat(text) {
    if (!text || typeof text !== 'string' || !text.includes('|')) return text;

    const lines = text.split('\n');
    const outputLines = [];
    let i = 0;

    while (i < lines.length) {
        const line = lines[i];
        const stripped = line.trim();

        if (
            stripped.startsWith('|') &&
            stripped.endsWith('|') &&
            i + 1 < lines.length &&
            /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$/.test(lines[i + 1].trim())
        ) {
            const rawHeaders = stripped.replace(/^\||\|$/g, '').split('|').map(c => c.trim().replace(/^\*+|\*+$/g, ''));
            i += 2; // Skip header and separator

            const tableRows = [];
            while (i < lines.length) {
                const rowLine = lines[i].trim();
                if (!rowLine.startsWith('|') || !rowLine.includes('|')) break;
                const rawCells = rowLine.replace(/^\||\|$/g, '').split('|').map(c => c.trim());
                tableRows.push(rawCells);
                i += 1;
            }

            const formattedBullets = [];
            for (const cells of tableRows) {
                const cleanedCells = cells.map(cell => cell.replace(/<\s*br\s*\/?>/gi, '\n    ').trim());
                if (cleanedCells.length >= 2) {
                    const cleanK = cleanedCells[0].replace(/^\*+|\*+$/g, '').trim();
                    const v = cleanedCells[1];
                    if (cleanedCells.length === 2) {
                        if (v.includes('\n')) {
                            formattedBullets.push(`• **${cleanK}:**\n    ${v}`);
                        } else {
                            formattedBullets.push(`• **${cleanK}:** ${v}`);
                        }
                    } else {
                        const restParts = [];
                        for (let j = 1; j < cleanedCells.length; j++) {
                            const h = rawHeaders[j] || `Col ${j + 1}`;
                            if (cleanedCells[j]) restParts.push(`*${h}*: ${cleanedCells[j]}`);
                        }
                        formattedBullets.push(`• **${cleanK}** — ${restParts.join(' | ')}`);
                    }
                } else if (cleanedCells.length === 1 && cleanedCells[0]) {
                    formattedBullets.push(`• ${cleanedCells[0]}`);
                }
            }

            if (formattedBullets.length > 0) {
                outputLines.push(formattedBullets.join('\n'));
            }
            continue;
        }

        outputLines.push(line);
        i += 1;
    }

    return outputLines.join('\n');
}

/**
 * Splits text into chunks safe for Telegram (limit is 4096, using 4000 for safety margin)
 */
function chunkMessage(text, maxLength = 4000) {
    if (!text || typeof text !== 'string') return [];
    if (text.length <= maxLength) return [text];

    const chunks = [];
    let remaining = text;

    while (remaining.length > maxLength) {
        let splitIdx = -1;

        // Try to split at paragraph boundary (\n\n)
        const paragraphIdx = remaining.lastIndexOf('\n\n', maxLength);
        if (paragraphIdx > maxLength * 0.5) {
            splitIdx = paragraphIdx + 2;
        } else {
            // Try single newline (\n)
            const lineIdx = remaining.lastIndexOf('\n', maxLength);
            if (lineIdx > maxLength * 0.5) {
                splitIdx = lineIdx + 1;
            } else {
                // Try space
                const spaceIdx = remaining.lastIndexOf(' ', maxLength);
                if (spaceIdx > maxLength * 0.5) {
                    splitIdx = spaceIdx + 1;
                } else {
                    // Hard cut if no clean break found
                    splitIdx = maxLength;
                }
            }
        }

        const chunk = remaining.substring(0, splitIdx).trim();
        if (chunk) chunks.push(chunk);
        remaining = remaining.substring(splitIdx).trim();
    }

    if (remaining.length > 0) {
        chunks.push(remaining);
    }

    return chunks;
}

/**
 * Sends a message in sequential chunks to avoid Telegram's 4096 character limit
 */
async function sendTelegramChunks(bot, chatId, text, baseOptions = {}) {
    const chunks = chunkMessage(text, 4000);
    if (chunks.length === 0) return;

    for (let i = 0; i < chunks.length; i++) {
        const options = { ...baseOptions };
        // Only quote the user message on the first chunk
        if (i > 0 && options.reply_to_message_id) {
            delete options.reply_to_message_id;
        }
        await bot.sendMessage(chatId, chunks[i], options);
        // Small delay between chunks to preserve delivery order and respect rate limits
        if (i < chunks.length - 1) {
            await new Promise(resolve => setTimeout(resolve, 300));
        }
    }
}

async function connectToTelegram() {
    console.log('[Bridge] Starting Jarvis Telegram Bridge...');

    const bot = new TelegramBot(BOT_TOKEN, { polling: true });
    globalBot = bot;

    // Get bot info to confirm connection
    try {
        const me = await bot.getMe();
        console.log(`✅ Jarvis Telegram Bridge connected as @${me.username}!`);
        console.log(`🔒 Listening for commands exclusively from owner ID: ${OWNER_ID}`);
        await sendStatus('telegram.status', 'connected');
    } catch (err) {
        console.error("❌ Failed to connect to Telegram:", err.message);
        await sendStatus('telegram.status', 'error');
        process.exit(1);
    }

    // Handle polling errors (network issues, etc.)
    bot.on('polling_error', async (error) => {
        console.error('[Polling Error]', error.message);
        
        // If there's a 409 Conflict, another bot instance is running (e.g. during deployment overlapping).
        // Exit this process gracefully so it doesn't aggressively spam Telegram and logs.
        if (error.message.includes('409 Conflict')) {
            console.error('[Bridge] Exiting to avoid 409 Conflict spam. The process will be restarted by the supervisor.');
            await bot.stopPolling();
            setTimeout(() => process.exit(1), 5000);
        }
        
        // Do not send polling_error to Jarvis frontend as it causes permanent "Offline" state
        // await sendStatus('telegram.status', 'polling_error');
    });

    // Handle incoming messages
    bot.on('message', async (msg) => {
        const chatId = msg.chat.id;
        const senderId = msg.from.id.toString();
        let text = msg.text || msg.caption || '';
        
        const hasMedia = !!(msg.photo || msg.document || msg.video || msg.audio || msg.voice);

        console.log(`\n[DEBUG] Message received from: ${senderId} (chat: ${chatId})`);

        // Security: only respond to the owner
        if (senderId !== OWNER_ID) {
            console.log(`[Security] Ignored message from unauthorized user: ${senderId}`);
            return;
        }

        if (!text && hasMedia) {
            text = "analyze this media";
        } else if (!text) {
            return;
        }

        console.log(`\n[Owner] ${text}`);

        // Send typing indicator
        await bot.sendChatAction(chatId, 'typing');

        let finalMessage = text;

        if (hasMedia) {
            try {
                let fileId;
                if (msg.photo && msg.photo.length > 0) {
                    fileId = msg.photo[msg.photo.length - 1].file_id;
                } else if (msg.document) {
                    fileId = msg.document.file_id;
                } else if (msg.video) {
                    fileId = msg.video.file_id;
                } else if (msg.audio) {
                    fileId = msg.audio.file_id;
                } else if (msg.voice) {
                    fileId = msg.voice.file_id;
                }

                if (fileId) {
                    const fileLink = await bot.getFileLink(fileId);
                    const response = await axios.get(fileLink, { responseType: 'arraybuffer' });
                    const buffer = Buffer.from(response.data, 'binary');
                    const base64Data = buffer.toString('base64');
                    const mimeType = response.headers['content-type'] || 'application/octet-stream';

                    finalMessage += `\n\n--- File: telegram_media ---\ndata:${mimeType};base64,${base64Data}\n--- End of telegram_media ---`;
                }
            } catch (err) {
                console.error("Failed to download media:", err.message);
            }
        }

        try {
            // Forward to Jarvis API with automatic local loopback retry if primary fails
            let response = null;
            const apiKeyHeader = { 'X-API-Key': process.env.JARVIS_SECRET_KEY || 'JARVIS_DEV_KEY' };
            try {
                response = await axios.post(`${JARVIS_BACKEND_URL}/api/chat`, {
                    message: finalMessage,
                    stream: false
                }, {
                    headers: apiKeyHeader,
                    timeout: 30000
                });
            } catch (primaryErr) {
                const fallbackUrl = `http://127.0.0.1:${localPort}/api/chat`;
                if (`${JARVIS_BACKEND_URL}/api/chat` !== fallbackUrl) {
                    console.warn(`[Bridge] Primary backend failed (${primaryErr.message}). Retrying via loopback ${fallbackUrl}...`);
                    response = await axios.post(fallbackUrl, {
                        message: finalMessage,
                        stream: false
                    }, {
                        headers: apiKeyHeader,
                        timeout: 30000
                    });
                } else {
                    throw primaryErr;
                }
            }

            // Extract plain text from the API response
            let data = response.data;
            if (typeof data === 'string') {
                try { data = JSON.parse(data); } catch (_) {}
            }

            let reply;
            const content = data?.content;

            if (typeof content === 'string') {
                // Try to parse content in case it's a JSON string
                try {
                    const parsed = JSON.parse(content);
                    // If it's a structured result (e.g. vision analysis), extract the summary
                    reply = parsed.summary || parsed.text || parsed.message || JSON.stringify(parsed, null, 2);
                } catch (_) {
                    // It's a plain text string — use as-is
                    reply = content;
                }
            } else if (typeof content === 'object' && content !== null) {
                // Content is already an object (vision result, tool output, etc.)
                reply = content.summary || content.text || content.message || JSON.stringify(content, null, 2);
            } else {
                reply = String(data);
            }

            if (!reply || !String(reply).trim()) {
                reply = "⚠️ Jarvis completed processing, but no text response was produced.";
            }

            reply = convertTablesToReadableFormat(reply);

        } catch (error) {
            console.error("Error communicating with Jarvis API:", error.message);
            try {
                await bot.sendMessage(chatId, "⚠️ Jarvis Backend is unreachable.", {
                    reply_to_message_id: msg.message_id
                });
            } catch (alertErr) {
                console.error("Failed to send unreachable alert to Telegram:", alertErr.message);
            }
            return;
        }

        // Send reply back via Telegram as plain text with chunking
        if (reply) {
            try {
                await sendTelegramChunks(bot, chatId, reply, {
                    reply_to_message_id: msg.message_id,
                    parse_mode: undefined
                });
                console.log(`[Jarvis] ${reply.substring(0, 80)}... (${reply.length} chars)`);
            } catch (sendErr) {
                console.error("Failed to send message to Telegram:", sendErr.message);
            }
        }
    });
}

// HTTP Server for Push Notifications & Status
const server = http.createServer((req, res) => {
    const url = req.url || '';
    if (req.method === 'GET' && (url === '/' || url === '/health' || url.startsWith('/health'))) {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
            status: 'ok',
            bridge: 'telegram',
            connected: !!globalBot,
            ownerId: OWNER_ID
        }));
        return;
    }

    if (req.method === 'POST' && (url === '/send' || url.startsWith('/send'))) {
        let body = '';
        req.on('data', chunk => { body += chunk.toString(); });
        req.on('end', async () => {
            try {
                const data = JSON.parse(body);
                if (!data.message) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'Field "message" is required' }));
                    return;
                }
                if (!globalBot) {
                    res.writeHead(503, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'Telegram bot is not connected yet' }));
                    return;
                }

                const targetChatId = data.to || data.chat_id || OWNER_ID;
                const messageText = convertTablesToReadableFormat(data.message);
                await sendTelegramChunks(globalBot, targetChatId, messageText);
                console.log(`[Bridge] Sent message to ${targetChatId}: "${messageText.substring(0, 60)}"`);
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ status: 'ok', recipient: targetChatId }));
            } catch (err) {
                console.error("Push Notification Error:", err);
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: err.message || 'Internal server error' }));
            }
        });
    } else {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Not Found' }));
    }
});

server.on('error', (err) => {
    console.error("[Bridge] HTTP Server error:", err.message);
});

const port = parseInt(process.env.TELEGRAM_BRIDGE_PORT || '3003', 10);
const host = process.env.TELEGRAM_BRIDGE_HOST || '0.0.0.0';
server.listen(port, host, () => {
    console.log(`[Bridge] HTTP Server listening on http://${host}:${port} for push notifications`);
});

connectToTelegram();
