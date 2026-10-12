require('dotenv').config({ path: '../../.env' });
const pino = require('pino');
const qrcode = require('qrcode');
const axios = require('axios');
const http = require('http');

const OWNER_NUMBER = process.env.WHATSAPP_OWNER_NUMBER;

if (!OWNER_NUMBER || OWNER_NUMBER === 'YOUR_NUMBER_HERE') {
    console.error("ERROR: WHATSAPP_OWNER_NUMBER is not set correctly in the .env file.");
    console.error("Please add it to ../../.env in the format: WHATSAPP_OWNER_NUMBER=1234567890");
    process.exit(1);
}

const formatNumber = (num) => `${num}@s.whatsapp.net`;
const ownerJid = formatNumber(OWNER_NUMBER.replace(/[^0-9]/g, ''));

const localPort = process.env.PORT || 8000;
const JARVIS_BACKEND_URL = (process.env.JARVIS_BACKEND_URL || `http://127.0.0.1:${localPort}`).replace(/\/+$/, '');
const JARVIS_EVENT_URL = `${JARVIS_BACKEND_URL}/api/whatsapp/event`;

let globalSock = null;
let isConnected = false;

// Debounce map: senderJid -> timestamp
const userLastMessage = new Map();
// Message ID deduplication set
const processedMessageIds = new Set();
// LRU message cache for Signal retry requests
const messageStore = new Map();

/**
 * Recursively unwraps nested Baileys message containers
 * (deviceSentMessage, ephemeralMessage, viewOnceMessage, documentWithCaptionMessage, etc.)
 */
function unwrapMessage(msgObj) {
    if (!msgObj) return null;
    let current = msgObj;
    let depth = 0;
    while (current && depth < 10) {
        if (current.deviceSentMessage?.message) {
            current = current.deviceSentMessage.message;
        } else if (current.ephemeralMessage?.message) {
            current = current.ephemeralMessage.message;
        } else if (current.viewOnceMessage?.message) {
            current = current.viewOnceMessage.message;
        } else if (current.viewOnceMessageV2?.message) {
            current = current.viewOnceMessageV2.message;
        } else if (current.viewOnceMessageV2Extension?.message) {
            current = current.viewOnceMessageV2Extension.message;
        } else if (current.documentWithCaptionMessage?.message) {
            current = current.documentWithCaptionMessage.message;
        } else if (current.editedMessage?.message) {
            current = current.editedMessage.message;
        } else if (current.protocolMessage?.editedMessage) {
            current = current.protocolMessage.editedMessage;
        } else {
            break;
        }
        depth++;
    }
    return current;
}

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

async function connectToWhatsApp() {
    const baileys = await import('@whiskeysockets/baileys');
    const makeWASocket = baileys.default || baileys.makeWASocket;
    const { useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion, downloadMediaMessage } = baileys;

    const path = require('path');
    const authFolder = process.env.WHATSAPP_AUTH_DIR
        ? process.env.WHATSAPP_AUTH_DIR
        : process.env.WEBSITE_SITE_NAME 
            ? path.join(process.env.HOME || process.env.USERPROFILE || '/home', 'site', 'auth_info_baileys')
            : path.join(__dirname, 'auth_info_baileys');

    const fs = require('fs');
    const credsPath = path.join(authFolder, 'creds.json');
    if (fs.existsSync(credsPath)) {
        try {
            const credsStr = fs.readFileSync(credsPath, 'utf8');
            const creds = JSON.parse(credsStr);
            if (creds && creds.me && creds.account && creds.registered === false) {
                console.log("Fixing corrupted creds.json (registered: false -> true)...");
                creds.registered = true;
                fs.writeFileSync(credsPath, JSON.stringify(creds, null, 2));
            }
        } catch (e) {
            console.error("Failed to parse creds.json during startup check:", e.message);
        }
    }

    const { state, saveCreds } = await useMultiFileAuthState(authFolder);
    const { version, isLatest } = await fetchLatestBaileysVersion();
    console.log(`[Bridge] Using WhatsApp Web v${version.join('.')}, isLatest: ${isLatest}`);

    const sock = makeWASocket({
        version,
        auth: state,
        printQRInTerminal: false,
        logger: pino({ level: 'silent' }),
        browser: ['Mac OS', 'Chrome', '121.0.0'],
        markOnlineOnConnect: false,
        syncFullHistory: false,
        generateHighQualityLinkPreview: false,
        qrTimeout: 60000,
        getMessage: async (key) => {
            return messageStore.get(key.id) || undefined;
        }
    });
    
    globalSock = sock; // Expose to HTTP server

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;
        
        if (qr) {
            console.log("Generating QR code to display in Jarvis Frontend...");
            qrcode.toDataURL(qr, async (err, url) => {
                if (err) {
                    console.error("Error generating QR code", err);
                    return;
                }
                await sendStatus('whatsapp.qr', url);
            });
        }
        
        if (connection === 'close') {
            isConnected = false;
            const statusCode = lastDisconnect?.error?.output?.statusCode;
            const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
            
            if (statusCode === DisconnectReason.loggedOut) {
                console.log('Connection closed: Logged out.');
            } else {
                console.log(`Connection closed due to ${lastDisconnect?.error?.message || lastDisconnect?.error}. Reconnecting: ${shouldReconnect}`);
            }

            sendStatus('whatsapp.status', 'disconnected');
            
            if (statusCode === 401) {
                console.log("⚠️ 401 Unauthorized. The WhatsApp session is corrupted or unlinked.");
                console.log(`Deleting ${authFolder} to force a fresh QR code scan...`);
                const fs = require('fs');
                if (fs.existsSync(authFolder)) {
                    fs.rmSync(authFolder, { recursive: true, force: true });
                }
                console.log("Restarting connection...");
                connectToWhatsApp();
            } else if (statusCode === 408) {
                console.log("⚠️ 408 Request Timeout. QR code scanning timed out.");
                console.log("Restarting connection...");
                connectToWhatsApp();
            } else if (shouldReconnect) {
                connectToWhatsApp();
            }
        } else if (connection === 'open') {
            isConnected = true;
            console.log('✅ Jarvis WhatsApp Bridge connected!');
            console.log(`🔒 Listening for commands exclusively from: ${ownerJid}`);
            sendStatus('whatsapp.status', 'connected');
        }
    });

    sock.ev.on('messages.upsert', async (m) => {
        // Handle both live notify events and companion device append syncs
        if (m.type !== 'notify' && m.type !== 'append') return;
        
        for (const msg of m.messages) {
            if (!msg.message) continue;

            // If the message is older than 2 minutes (e.g. historical chat sync on startup), ignore it
            const rawTimestamp = msg.messageTimestamp;
            const msgTimestamp = rawTimestamp
                ? (typeof rawTimestamp === 'number' ? rawTimestamp * 1000 : Number(rawTimestamp) * 1000)
                : Date.now();
            if (msgTimestamp && (Date.now() - msgTimestamp > 120000)) {
                continue;
            }

            // Cache message for Signal protocol retry receipts
            if (msg.key?.id) {
                messageStore.set(msg.key.id, msg.message);
                if (messageStore.size > 200) {
                    const oldest = messageStore.keys().next().value;
                    messageStore.delete(oldest);
                }
            }

            // Normalize JIDs (remove device suffix like :12)
            const rawSender = msg.key?.remoteJid;
            if (!rawSender || rawSender === 'status@broadcast') continue;

            let senderId = rawSender;
            if (rawSender.includes(':')) {
                const base = rawSender.split(':')[0];
                const domain = rawSender.split('@')[1];
                senderId = `${base}@${domain}`;
            }
            const isOwner = (jid) => jid && typeof jid === 'string' && jid.replace(/\D/g, '').endsWith(OWNER_NUMBER.replace(/\D/g, ''));
            
            const authId = state.creds?.me?.id ? state.creds.me.id.split(':')[0] + '@s.whatsapp.net' : null;
            const authLid = state.creds?.me?.lid ? state.creds.me.lid.split(':')[0] + '@lid' : null;
            const userLid = sock.user?.lid ? sock.user.lid.split(':')[0] + '@lid' : authLid;
            const userId = sock.user?.id ? sock.user.id.split(':')[0] + '@s.whatsapp.net' : authId;
            
            // A message is a self-chat if it's sent to the owner's number, or the user's lid, or the user's own JID.
            const isSelfChat = isOwner(senderId) || (userLid && senderId === userLid) || (userId && senderId === userId);

            console.log(`\n[DEBUG] Message received from: ${rawSender} | fromMe: ${msg.key.fromMe} | isSelfChat: ${isSelfChat} (userLid: ${userLid}, userId: ${userId})`);

            // If the message is outgoing to someone else, ignore it.
            if (msg.key.fromMe && !isSelfChat) {
                console.log(`[DEBUG] Ignoring outgoing message to someone else (${rawSender})`);
                continue;
            }
            
            // If it's an incoming message, make sure it's strictly from the owner
            if (!msg.key.fromMe && !isSelfChat) {
                console.log(`[Security] Ignored message from unauthorized number: ${senderId}`);
                continue;
            }

            // Unwrap Baileys wrappers (critical for deviceSentMessage when messaging from phone/self-chat)
            const unwrappedMessage = unwrapMessage(msg.message);

            // Extract plain text from message
            const extractText = (message) => {
                if (!message) return '';
                if (typeof message.conversation === 'string') return message.conversation;
                if (typeof message.extendedTextMessage?.text === 'string') return message.extendedTextMessage.text;
                if (typeof message.imageMessage?.caption === 'string') return message.imageMessage.caption;
                if (typeof message.videoMessage?.caption === 'string') return message.videoMessage.caption;
                if (typeof message.documentMessage?.caption === 'string') return message.documentMessage.caption;
                if (typeof message.buttonsResponseMessage?.selectedDisplayText === 'string') return message.buttonsResponseMessage.selectedDisplayText;
                if (typeof message.templateButtonReplyMessage?.selectedDisplayText === 'string') return message.templateButtonReplyMessage.selectedDisplayText;
                if (typeof message.listResponseMessage?.title === 'string') return message.listResponseMessage.title;
                return '';
            };
            
            // Check for media
            const checkHasMedia = (message) => {
                if (!message) return false;
                return !!(message.imageMessage || message.videoMessage || message.documentMessage || message.audioMessage);
            };

            let text = extractText(unwrappedMessage);
            const hasMedia = checkHasMedia(unwrappedMessage);

            if (!text && hasMedia) {
                text = "analyze this media";
            } else if (!text) {
                const keys = msg.message ? Object.keys(msg.message).join(', ') : 'none';
                console.log(`[DEBUG] No text/media in message (keys: [${keys}]), skipping.`);
                continue;
            }

            // Loop-proofing: Prevent Jarvis from responding to its own replies
            if (text.startsWith('[Jarvis]:')) {
                console.log('[DEBUG] Skipping Jarvis bot reply to prevent echo loop');
                continue;
            }

            // Check if trigger prefix is present.
            // Recognizes "jarvis", "hey jarvis", "hi jarvis", "ok jarvis", "/jarvis" (case-insensitive)
            // If WHATSAPP_REQUIRE_PREFIX is explicitly set to "false", responds to all messages.
            const requirePrefix = process.env.WHATSAPP_REQUIRE_PREFIX !== 'false';
            const triggerRegex = /^(jarvis|hey jarvis|hi jarvis|ok jarvis|\/jarvis)[,\s:]*/i;
            const hasTrigger = triggerRegex.test(text.trim());

            if (requirePrefix && !hasTrigger) {
                console.log(`[DEBUG] Ignored message without trigger prefix: "${text.length > 50 ? text.substring(0, 50) + '...' : text}"`);
                continue;
            }

            // Deduplication by message ID
            if (msg.key.id) {
                if (processedMessageIds.has(msg.key.id)) {
                    console.log(`[DEBUG] Dropping duplicate message event: ${msg.key.id}`);
                    continue;
                }
                processedMessageIds.add(msg.key.id);
                if (processedMessageIds.size > 500) {
                    const oldest = processedMessageIds.values().next().value;
                    processedMessageIds.delete(oldest);
                }
            }

            // Debounce rapid-fire messages (default 1500ms)
            const now = Date.now();
            const debounceMs = parseInt(process.env.WHATSAPP_DEBOUNCE_MS || '1500', 10);
            const lastMsgTime = userLastMessage.get(rawSender) || 0;
            if (now - lastMsgTime < debounceMs) {
                console.log(`[Debounce] Dropped rapid-fire message from ${rawSender} (${now - lastMsgTime}ms < ${debounceMs}ms)`);
                continue;
            }
            userLastMessage.set(rawSender, now);

            console.log(`\n[Owner] ${text}`);

            // Strip the trigger prefix before forwarding to AI (or keep whole text if only trigger word was sent)
            let finalMessage = hasTrigger
                ? text.trim().replace(triggerRegex, '').trim() || text.trim()
                : text.trim();

            // Resolve target JID for sending reply:
            // In self-chat, sending back to ownerJid (@s.whatsapp.net) ensures the message
            // arrives in the user's primary chat rather than getting lost on an unroutable @lid.
            const replyTarget = isSelfChat ? ownerJid : (rawSender.endsWith('@lid') && userId ? userId : rawSender);

            // Send typing indicator
            if (globalSock) {
                try {
                    await globalSock.sendPresenceUpdate('composing', replyTarget);
                } catch (_) {}
            }

            if (hasMedia) {
                try {
                    const unwrappedMsg = {
                        ...msg,
                        message: unwrappedMessage
                    };
                    const buffer = await downloadMediaMessage(
                        unwrappedMsg,
                        'buffer',
                        { },
                        { 
                            logger: pino({ level: 'silent' }),
                            reuploadRequest: globalSock.updateMediaMessage
                        }
                    );
                    
                    const mimeType = unwrappedMessage?.imageMessage?.mimetype || 
                                     unwrappedMessage?.videoMessage?.mimetype || 
                                     unwrappedMessage?.audioMessage?.mimetype || 
                                     unwrappedMessage?.documentMessage?.mimetype || 
                                     'application/octet-stream';
                                     
                    const base64Data = buffer.toString('base64');
                    finalMessage += `\n\n--- File: whatsapp_media ---\ndata:${mimeType};base64,${base64Data}\n--- End of whatsapp_media ---`;
                } catch (err) {
                    console.error("Failed to download media:", err.message);
                }
            }

            let reply = null;
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

                const content = data?.content;
                if (typeof content === 'string') {
                    try {
                        const parsed = JSON.parse(content);
                        reply = parsed.summary || parsed.text || parsed.message || JSON.stringify(parsed, null, 2);
                    } catch (_) {
                        reply = content;
                    }
                } else if (typeof content === 'object' && content !== null) {
                    reply = content.summary || content.text || content.message || JSON.stringify(content, null, 2);
                } else {
                    reply = String(data);
                }
                
                if (!reply.startsWith('[Jarvis]: ')) {
                    reply = `[Jarvis]: ${reply}`;
                }
            } catch (error) {
                console.error("Error communicating with Jarvis API:", error.message);
                reply = "⚠️ Jarvis Backend is unreachable.";
            }

            // Send reply back via WhatsApp
            if (reply && globalSock) {
                try {
                    await globalSock.sendMessage(replyTarget, { text: reply }, { quoted: msg });
                    console.log(`[Jarvis] ${reply}`);
                } catch (sendErr) {
                    console.warn(`[Bridge] Quoted send failed (${sendErr.message}), sending unquoted to ${replyTarget}...`);
                    try {
                        await globalSock.sendMessage(replyTarget, { text: reply });
                        console.log(`[Jarvis] ${reply}`);
                    } catch (retryErr) {
                        console.error(`[Bridge] Failed to send reply to ${replyTarget}:`, retryErr.message);
                    }
                }
            }

            if (globalSock) {
                try {
                    await globalSock.sendPresenceUpdate('paused', replyTarget);
                } catch (_) {}
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
            bridge: 'whatsapp',
            connected: isConnected,
            ownerJid: ownerJid
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
                if (!globalSock || !isConnected) {
                    res.writeHead(503, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'WhatsApp is not connected yet' }));
                    return;
                }

                // Resolve target recipient (defaults to ownerJid)
                let targetJid = ownerJid;
                const recipient = data.to || data.recipient || data.phone_number;
                if (recipient) {
                    const cleanNum = String(recipient).replace(/[^0-9]/g, '');
                    if (cleanNum) {
                        targetJid = formatNumber(cleanNum);
                    }
                }

                await globalSock.sendMessage(targetJid, { text: data.message });
                console.log(`[Bridge] Sent message to ${targetJid}: "${data.message.substring(0, 60)}"`);
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ status: 'ok', recipient: targetJid }));
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

const port = parseInt(process.env.WHATSAPP_BRIDGE_PORT || '3002', 10);
const host = process.env.WHATSAPP_BRIDGE_HOST || '0.0.0.0';
server.listen(port, host, () => {
    console.log(`[Bridge] HTTP Server listening on http://${host}:${port} for push notifications`);
});

// Keep-alive / Connection check every 2 minutes
setInterval(async () => {
    // Only check presence if the socket is actively connected and authenticated
    if (globalSock && isConnected && globalSock.user) {
        try {
            // Verify connection is alive by sending a presence update
            await globalSock.sendPresenceUpdate('available');
            console.log("[Bridge] Connection check (2 min): OK");
        } catch (error) {
            console.error("[Bridge] Connection check failed, connection might be stale:", error.message);
            try { 
                globalSock.ws.close(); 
            } catch (e) {} // Force disconnect to trigger reconnect
        }
    }
}, 120000);

connectToWhatsApp();
