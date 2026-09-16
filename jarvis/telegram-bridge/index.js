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

const JARVIS_BACKEND_URL = process.env.JARVIS_BACKEND_URL || 'http://127.0.0.1:8000';
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
            // Forward to Jarvis API
            const response = await axios.post(`${JARVIS_BACKEND_URL}/api/chat`, {
                message: finalMessage,
                stream: false
            }, {
                headers: { 'X-API-Key': process.env.JARVIS_SECRET_KEY || 'JARVIS_DEV_KEY' }
            });

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


            // Send reply back via Telegram as plain text
            await bot.sendMessage(chatId, reply, {
                reply_to_message_id: msg.message_id,
                parse_mode: undefined
            });
            console.log(`[Jarvis] ${reply}`);

        } catch (error) {
            console.error("Error communicating with Jarvis API:", error.message);
            await bot.sendMessage(chatId, "⚠️ Jarvis Backend is unreachable.", {
                reply_to_message_id: msg.message_id
            });
        }
    });
}

// HTTP Server for Push Notifications
const server = http.createServer((req, res) => {
    if (req.method === 'POST' && req.url === '/send') {
        let body = '';
        req.on('data', chunk => { body += chunk.toString(); });
        req.on('end', async () => {
            try {
                const data = JSON.parse(body);
                if (data.message && globalBot) {
                    await globalBot.sendMessage(OWNER_ID, data.message);
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ status: 'ok' }));
                } else {
                    res.writeHead(400);
                    res.end(JSON.stringify({ error: 'Bad Request or not connected' }));
                }
            } catch (err) {
                console.error("Push Notification Error:", err);
                res.writeHead(500);
                res.end('Error');
            }
        });
    } else {
        res.writeHead(404);
        res.end('Not Found');
    }
});

server.listen(3002, () => {
    console.log('[Bridge] HTTP Server listening on port 3002 for push notifications');
});

connectToTelegram();
