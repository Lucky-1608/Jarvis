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

const JARVIS_BACKEND_URL = process.env.JARVIS_BACKEND_URL || 'http://127.0.0.1:8000';
const JARVIS_EVENT_URL = `${JARVIS_BACKEND_URL}/api/whatsapp/event`;

let globalSock = null;

// Debounce map: senderJid -> timestamp
const userLastMessage = new Map();

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
        qrTimeout: 60000
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
            console.log('✅ Jarvis WhatsApp Bridge connected!');
            console.log(`🔒 Listening for commands exclusively from: ${ownerJid}`);
            sendStatus('whatsapp.status', 'connected');
        }
    });

    sock.ev.on('messages.upsert', async (m) => {
        if (m.type !== 'notify') return;
        
        for (const msg of m.messages) {
            if (!msg.message) continue;

            // Normalize JIDs (remove device suffix like :12)
            const rawSender = msg.key.remoteJid;
            const senderId = rawSender.includes(':') ? rawSender.split(':')[0] + '@s.whatsapp.net' : rawSender;
            const isOwner = (jid) => jid.replace(/\D/g, '').endsWith(OWNER_NUMBER.replace(/\D/g, ''));
            const userLid = sock.user?.lid ? sock.user.lid.split(':')[0] + '@lid' : null;
            const isSelfChat = isOwner(senderId) || senderId === userLid;

            console.log(`\n[DEBUG] Message received from: ${rawSender} | fromMe: ${msg.key.fromMe}`);

            // If the message is outgoing to someone else, ignore it.
            if (msg.key.fromMe && !isSelfChat) {
                continue;
            }
            
            // If it's an incoming message, make sure it's strictly from the owner
            if (!msg.key.fromMe && !isSelfChat) {
                console.log(`[Security] Ignored message from unauthorized number: ${senderId}`);
                continue;
            }

            // Extract text message
            let text = msg.message.conversation || 
                         msg.message.extendedTextMessage?.text || 
                         msg.message.imageMessage?.caption || '';

            const hasMedia = !!(msg.message.imageMessage || msg.message.videoMessage || msg.message.documentMessage || msg.message.audioMessage);

            if (!text && hasMedia) {
                text = "jarvis, analyze this media";
            } else if (!text) {
                continue;
            }

            // Check if the trigger word "jarvis" is present
            if (!text.toLowerCase().includes('jarvis')) {
                continue;
            }

            // Loop-proofing: Prevent Jarvis from responding to its own replies
            if (text.startsWith('[Jarvis]:')) {
                continue;
            }

            // Debounce: Ignore messages if sent within 5 seconds of the last one
            const now = Date.now();
            const lastMsgTime = userLastMessage.get(rawSender) || 0;
            if (now - lastMsgTime < 5000) {
                console.log(`[Debounce] Dropped rapid-fire message from ${rawSender}`);
                continue;
            }
            userLastMessage.set(rawSender, now);

            console.log(`\n[Owner] ${text}`);
            
            // Send typing indicator
            await sock.sendPresenceUpdate('composing', rawSender);

            let finalMessage = text;
            
            if (hasMedia) {
                try {
                    const buffer = await downloadMediaMessage(
                        msg,
                        'buffer',
                        { },
                        { 
                            logger: pino({ level: 'silent' }),
                            reuploadRequest: sock.updateMediaMessage
                        }
                    );
                    
                    const mimeType = msg.message.imageMessage?.mimetype || 
                                     msg.message.videoMessage?.mimetype || 
                                     msg.message.audioMessage?.mimetype || 
                                     msg.message.documentMessage?.mimetype || 
                                     'application/octet-stream';
                                     
                    const base64Data = buffer.toString('base64');
                    finalMessage += `\n\n--- File: whatsapp_media ---\ndata:${mimeType};base64,${base64Data}\n--- End of whatsapp_media ---`;
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

                // Send reply back via WhatsApp
                await sock.sendMessage(rawSender, { text: reply }, { quoted: msg });
                console.log(`[Jarvis] ${reply}`);

            } catch (error) {
                console.error("Error communicating with Jarvis API:", error.message);
                await sock.sendMessage(rawSender, { text: "⚠️ Jarvis Backend is unreachable." }, { quoted: msg });
            } finally {
                await sock.sendPresenceUpdate('paused', rawSender);
            }
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
                if (data.message && globalSock) {
                    await globalSock.sendMessage(ownerJid, { text: data.message });
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

server.listen(3001, () => {
    console.log('[Bridge] HTTP Server listening on port 3001 for push notifications');
});

connectToWhatsApp();
