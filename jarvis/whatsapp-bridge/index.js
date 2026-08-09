require('dotenv').config({ path: '../../.env' });
const { makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const pino = require('pino');
const qrcode = require('qrcode');
const axios = require('axios');

const OWNER_NUMBER = process.env.WHATSAPP_OWNER_NUMBER;

if (!OWNER_NUMBER || OWNER_NUMBER === 'YOUR_NUMBER_HERE') {
    console.error("ERROR: WHATSAPP_OWNER_NUMBER is not set correctly in the .env file.");
    console.error("Please add it to ../../.env in the format: WHATSAPP_OWNER_NUMBER=1234567890");
    process.exit(1);
}

const formatNumber = (num) => `${num}@s.whatsapp.net`;
const ownerJid = formatNumber(OWNER_NUMBER.replace(/[^0-9]/g, ''));

const JARVIS_EVENT_URL = 'http://127.0.0.1:8000/api/whatsapp/event';

// Debounce map: senderJid -> timestamp
const userLastMessage = new Map();

async function sendStatus(status, data = null) {
    try {
        await axios.post(JARVIS_EVENT_URL, {
            type: status,
            data: data
        }, {
            headers: { 'X-API-Key': 'JARVIS_DEV_KEY' }
        });
    } catch (err) {
        console.error("Could not send status to Jarvis:", err.message);
    }
}

async function connectToWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState('auth_info_baileys');
    const { version, isLatest } = await fetchLatestBaileysVersion();
    console.log(`[Bridge] Using WhatsApp Web v${version.join('.')}, isLatest: ${isLatest}`);

    const sock = makeWASocket({
        version,
        auth: state,
        printQRInTerminal: false,
        logger: pino({ level: 'silent' }),
        browser: ['Jarvis OS', 'Chrome', '1.0.0']
    });

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
            console.log('Connection closed due to', lastDisconnect?.error, ', reconnecting:', shouldReconnect);
            sendStatus('whatsapp.status', 'disconnected');
            
            if (statusCode === 401) {
                console.log("⚠️ 401 Unauthorized. The WhatsApp session is corrupted or unlinked.");
                console.log("Deleting auth_info_baileys to force a fresh QR code scan...");
                const fs = require('fs');
                if (fs.existsSync('auth_info_baileys')) {
                    fs.rmSync('auth_info_baileys', { recursive: true, force: true });
                }
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
            const text = msg.message.conversation || 
                         msg.message.extendedTextMessage?.text || 
                         msg.message.imageMessage?.caption;

            if (!text) continue;

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

            try {
                // Forward to Jarvis API
                const response = await axios.post('http://127.0.0.1:8000/api/chat', {
                    message: text,
                    stream: false
                }, {
                    headers: { 'X-API-Key': 'JARVIS_DEV_KEY' }
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

connectToWhatsApp();
