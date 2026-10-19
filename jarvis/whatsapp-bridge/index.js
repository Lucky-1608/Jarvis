require('dotenv').config({ path: '../../.env' });
const path = require('path');
const fs = require('fs');
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

// Container lifecycle & instance tracking (prevents dual-container conflict on Azure deployments)
const instanceId = `${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
const lockFolder = process.env.WEBSITE_SITE_NAME 
    ? path.join(process.env.HOME || process.env.USERPROFILE || '/home', 'site')
    : __dirname;
const instanceLockPath = path.join(lockFolder, 'whatsapp_instance.id');

try {
    if (!fs.existsSync(lockFolder)) fs.mkdirSync(lockFolder, { recursive: true });
    fs.writeFileSync(instanceLockPath, instanceId, 'utf8');
} catch (_) {}

function isCurrentInstance() {
    try {
        if (fs.existsSync(instanceLockPath)) {
            const current = fs.readFileSync(instanceLockPath, 'utf8').trim();
            return current === instanceId;
        }
    } catch (_) {}
    return true;
}

const authFolder = process.env.WHATSAPP_AUTH_DIR
    ? process.env.WHATSAPP_AUTH_DIR
    : process.env.WEBSITE_SITE_NAME 
        ? path.join(process.env.HOME || process.env.USERPROFILE || '/home', 'site', 'auth_info_baileys')
        : path.join(__dirname, 'auth_info_baileys');

const credsPath = path.join(authFolder, 'creds.json');
const credsBakPath = path.join(authFolder, 'creds.json.bak');

let globalSock = null;
let isConnected = false;
let reconnectTimeout = null;
let lastEmittedQr = null;

function scheduleReconnect(delayMs = 5000) {
    if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
        reconnectTimeout = null;
    }
    reconnectTimeout = setTimeout(() => {
        reconnectTimeout = null;
        if (isCurrentInstance()) {
            connectToWhatsApp();
        }
    }, delayMs);
}

// Debounce map: senderJid -> timestamp
const userLastMessage = new Map();
// Message ID deduplication set
const processedMessageIds = new Set();
// LRU message cache for Signal retry requests (stores both incoming and outgoing messages)
const messageStore = new Map();

function cacheMessage(keyId, message) {
    if (!keyId || !message) return;
    messageStore.set(keyId, message);
    if (messageStore.size > 2000) {
        const oldest = messageStore.keys().next().value;
        messageStore.delete(oldest);
    }
}

// In-memory retry counter cache store for Baileys (prevents infinite retry loops across reconnects)
const retryCounterMap = new Map();
const msgRetryCounterCache = {
    get: (key) => retryCounterMap.get(key),
    set: (key, value) => {
        retryCounterMap.set(key, value);
        if (retryCounterMap.size > 1000) {
            const oldest = retryCounterMap.keys().next().value;
            retryCounterMap.delete(oldest);
        }
    },
    del: (key) => retryCounterMap.delete(key),
    flushAll: () => retryCounterMap.clear()
};

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
 * Splits text into chunks safe for WhatsApp (4000 characters per chunk)
 */
function chunkMessage(text, maxLength = 4000) {
    if (!text || typeof text !== 'string') return [];
    if (text.length <= maxLength) return [text];

    const chunks = [];
    let remaining = text;

    while (remaining.length > maxLength) {
        let splitIdx = -1;

        const paragraphIdx = remaining.lastIndexOf('\n\n', maxLength);
        if (paragraphIdx > maxLength * 0.5) {
            splitIdx = paragraphIdx + 2;
        } else {
            const lineIdx = remaining.lastIndexOf('\n', maxLength);
            if (lineIdx > maxLength * 0.5) {
                splitIdx = lineIdx + 1;
            } else {
                const spaceIdx = remaining.lastIndexOf(' ', maxLength);
                if (spaceIdx > maxLength * 0.5) {
                    splitIdx = spaceIdx + 1;
                } else {
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
 * Sends a message in sequential chunks to avoid buffer drops or socket timeouts in Baileys
 */
async function sendWhatsAppChunks(sock, targetJid, text, quotedMsg = null) {
    const chunks = chunkMessage(text, 4000);
    if (chunks.length === 0) return;

    // Safety: Never quote a fromMe message or self-chat message.
    // Quoting fromMe stanzas across multi-device companion sessions corrupts the Signal ratchet
    // and causes permanent "Waiting for this message" decryption failures.
    const isFromMe = quotedMsg?.key?.fromMe;
    const effectiveQuoted = isFromMe ? null : quotedMsg;

    for (let i = 0; i < chunks.length; i++) {
        const chunk = chunks[i];
        const quoteOpt = (i === 0 && effectiveQuoted) ? { quoted: effectiveQuoted } : {};
        try {
            const sent = await sock.sendMessage(targetJid, { text: chunk }, quoteOpt);
            if (sent?.key?.id && sent?.message) {
                cacheMessage(sent.key.id, sent.message);
            }
        } catch (sendErr) {
            console.warn(`[Bridge] Quoted send failed (${sendErr.message}), sending unquoted to ${targetJid}...`);
            try {
                const sent = await sock.sendMessage(targetJid, { text: chunk });
                if (sent?.key?.id && sent?.message) {
                    cacheMessage(sent.key.id, sent.message);
                }
            } catch (retryErr) {
                console.error(`[Bridge] Failed to send reply chunk ${i + 1}/${chunks.length} to ${targetJid}:`, retryErr.message);
            }
        }
        if (i < chunks.length - 1) {
            await new Promise(resolve => setTimeout(resolve, 300));
        }
    }
}

async function connectToWhatsApp() {
    if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
        reconnectTimeout = null;
    }

    // Safely tear down existing socket and remove listeners before reconnecting
    if (globalSock) {
        try {
            globalSock.ev.removeAllListeners();
            if (globalSock.ws) {
                globalSock.ws.close();
            }
            if (globalSock.end) {
                globalSock.end(undefined);
            }
        } catch (_) {}
        globalSock = null;
    }

    const baileys = await import('@whiskeysockets/baileys');
    const makeWASocket = baileys.default || baileys.makeWASocket;
    const { useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion, downloadMediaMessage, makeCacheableSignalKeyStore, Browsers } = baileys;

    // Self-healing credentials check:
    // Only attempt recovery or wipe if creds.json exists but is completely corrupt (unparseable or empty).
    if (fs.existsSync(credsPath)) {
        try {
            const credsStr = fs.readFileSync(credsPath, 'utf8');
            if (!credsStr || credsStr.trim() === '') {
                throw new Error("creds.json is empty");
            }
            const creds = JSON.parse(credsStr);
            if (creds?.me && creds?.registered === true) {
                // Valid registered session — update backup copy
                try { fs.writeFileSync(credsBakPath, credsStr, 'utf8'); } catch (_) {}
            }
        } catch (e) {
            console.error("[Bridge] Failed to parse creds.json during startup check:", e.message);
            let restored = false;
            if (fs.existsSync(credsBakPath)) {
                try {
                    const bakStr = fs.readFileSync(credsBakPath, 'utf8');
                    const bakJson = JSON.parse(bakStr);
                    if (bakJson?.me && bakJson?.registered === true) {
                        console.log("[Bridge] Restoring valid registered creds.json from creds.json.bak...");
                        fs.writeFileSync(credsPath, bakStr, 'utf8');
                        restored = true;
                    }
                } catch (bakErr) {
                    console.error("[Bridge] Failed to restore from backup:", bakErr.message);
                }
            }
            if (!restored) {
                console.log("[Bridge] Clearing unrecoverable corrupt auth folder...");
                try { fs.rmSync(authFolder, { recursive: true, force: true }); } catch (_) {}
            }
        }
    }

    const { state, saveCreds } = await useMultiFileAuthState(authFolder);
    
    // Resolve WhatsApp Web protocol version with modern fallback
    let version = [2, 3000, 1043857760];
    try {
        const vData = await fetchLatestBaileysVersion();
        if (vData?.version) {
            version = vData.version;
            console.log(`[Bridge] Using WhatsApp Web v${version.join('.')}, isLatest: ${vData.isLatest}`);
        }
    } catch (verErr) {
        console.warn(`[Bridge] Could not fetch latest Baileys version (${verErr.message}), using fallback v${version.join('.')}`);
    }

    // Standard Desktop browser tuple (Chrome on Ubuntu) for smooth WhatsApp Web companion linking
    const browserConfig = Browsers?.ubuntu ? Browsers.ubuntu('Chrome') : ['Ubuntu', 'Chrome', '22.04.4'];

    const sock = makeWASocket({
        version,
        auth: {
            creds: state.creds,
            keys: makeCacheableSignalKeyStore(state.keys, pino({ level: 'silent' }))
        },
        msgRetryCounterCache,
        printQRInTerminal: false,
        logger: pino({ level: 'silent' }),
        browser: browserConfig,
        markOnlineOnConnect: false,
        syncFullHistory: false,
        generateHighQualityLinkPreview: false,
        qrTimeout: 60000,
        getMessage: async (key) => {
            if (key?.id) {
                const cached = messageStore.get(key.id);
                if (cached) return cached;
            }
            return undefined;
        }
    });

    
    globalSock = sock; // Expose to HTTP server

    // Safe credentials saver that updates backup copy upon successful write
    const safeSaveCreds = async () => {
        try {
            await saveCreds();
            if (fs.existsSync(credsPath)) {
                const data = fs.readFileSync(credsPath, 'utf8');
                if (data && data.length > 50) {
                    try {
                        const parsed = JSON.parse(data);
                        if (parsed?.me && parsed?.registered) {
                            fs.writeFileSync(credsBakPath, data, 'utf8');
                        }
                    } catch (_) {}
                }
            }
        } catch (err) {
            console.error("[Bridge] Failed to save creds safely:", err.message);
        }
    };

    sock.ev.on('creds.update', safeSaveCreds);

    // Support Pairing Code linking when configured via env
    const usePairingCode = process.env.WHATSAPP_USE_PAIRING_CODE === 'true' || process.env.WHATSAPP_AUTH_METHOD === 'pairing_code';
    if (usePairingCode && !state.creds?.registered) {
        const cleanPhone = OWNER_NUMBER.replace(/[^0-9]/g, '');
        if (cleanPhone) {
            setTimeout(async () => {
                if (sock.authState?.creds?.registered) return;
                try {
                    console.log(`[Bridge] Requesting Pairing Code for phone: ${cleanPhone}...`);
                    const code = await sock.requestPairingCode(cleanPhone);
                    console.log("\n================ WHATSAPP PAIRING CODE ================");
                    console.log(`🔑 PAIRING CODE: ${code}`);
                    console.log("Open WhatsApp > Linked Devices > Link a Device > Link with phone number instead");
                    console.log("=======================================================\n");
                    await sendStatus('whatsapp.pairing_code', code);
                } catch (pairErr) {
                    console.error("[Bridge] Pairing code request failed:", pairErr.message);
                }
            }, 4000);
        }
    }

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;
        
        if (qr && !usePairingCode) {
            if (qr !== lastEmittedQr) {
                lastEmittedQr = qr;
                console.log("[Bridge] QR code updated. Sending to Jarvis Frontend...");
                qrcode.toDataURL(qr, async (err, url) => {
                    if (err) {
                        console.error("[Bridge] Error generating QR code data URL:", err.message);
                        return;
                    }
                    await sendStatus('whatsapp.qr', url);
                });
            }
        }
        
        if (connection === 'close') {
            isConnected = false;
            const statusCode = lastDisconnect?.error?.output?.statusCode;
            const errorMsg = String(lastDisconnect?.error?.message || lastDisconnect?.error || '');
            const isConflict = statusCode === 440 || errorMsg.toLowerCase().includes('conflict');
            const shouldReconnect = statusCode !== DisconnectReason.loggedOut;

            // If a newer container instance has started during deployment, exit this process cleanly
            if (!isCurrentInstance()) {
                console.log(`[Bridge] Stale container detected (active instance took over). Exiting bridge process.`);
                process.exit(0);
                return;
            }

            sendStatus('whatsapp.status', 'disconnected');

            // 1) Explicit logout or 401 Unauthorized: session credentials permanently invalidated
            if (statusCode === DisconnectReason.loggedOut || statusCode === 401) {
                console.log("⚠️ Connection closed: Logged out (401). WhatsApp session is invalidated.");
                console.log(`Clearing ${authFolder} to allow a clean fresh login...`);
                try {
                    if (fs.existsSync(authFolder)) {
                        fs.rmSync(authFolder, { recursive: true, force: true });
                    }
                } catch (rmErr) {
                    console.error("Failed to delete authFolder:", rmErr.message);
                }
                lastEmittedQr = null;
                scheduleReconnect(3000);
                return;
            }

            // 2) Companion linking handshake (515 restart required): MUST NOT delete credentials!
            // WhatsApp companion handshake completes by closing socket 515 and restarting with exchanged keys.
            if (statusCode === DisconnectReason.restartRequired || statusCode === 515) {
                console.log("[Bridge] Restart required (515) after device pairing. Reconnecting with paired credentials in 2s...");
                scheduleReconnect(2000);
                return;
            }

            // 3) Session conflict (440): another active session connected
            if (isConflict) {
                console.log("[Bridge] WhatsApp session conflict detected. Backing off 10s before reconnect...");
                scheduleReconnect(10000);
                return;
            }

            // 4) QR timeout / connection timeout (408):
            if (statusCode === 408) {
                console.log("[Bridge] QR code scanning window timed out. Refreshing session in 3s...");
                scheduleReconnect(3000);
                return;
            }

            // 5) Any other normal disconnect / reconnect
            if (shouldReconnect) {
                console.log(`[Bridge] Connection closed (${statusCode || errorMsg}). Reconnecting in 5s...`);
                scheduleReconnect(5000);
            }
        } else if (connection === 'open') {
            isConnected = true;
            lastEmittedQr = null;
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
            if (msg.key?.id && msg.message) {
                cacheMessage(msg.key.id, msg.message);
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

                reply = convertTablesToReadableFormat(reply);
            } catch (error) {
                console.error("Error communicating with Jarvis API:", error.message);
                reply = "⚠️ Jarvis Backend is unreachable.";
            }

            // Send reply back via WhatsApp with chunking
            // In self-chat, NEVER quote the message: quoting a fromMe message across companion
            // sessions causes Signal ratchet collisions and permanent "Waiting for this message" errors.
            const quoteArg = (isSelfChat || msg.key?.fromMe) ? null : msg;
            if (reply && globalSock) {
                await sendWhatsAppChunks(globalSock, replyTarget, reply, quoteArg);
                console.log(`[Jarvis] ${reply.substring(0, 80)}... (${reply.length} chars)`);
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

                const messageToSend = convertTablesToReadableFormat(data.message);
                await sendWhatsAppChunks(globalSock, targetJid, messageToSend);
                console.log(`[Bridge] Sent message to ${targetJid}: "${messageToSend.substring(0, 60)}"`);
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ status: 'ok', recipient: targetJid }));
            } catch (err) {
                console.error("Push Notification Error:", err);
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: err.message || 'Internal server error' }));
            }
        });
    } else if (req.method === 'POST' && (url === '/reset' || url.startsWith('/reset'))) {
        console.log("[Bridge] Manual session reset requested via HTTP /reset");
        try {
            if (reconnectTimeout) {
                clearTimeout(reconnectTimeout);
                reconnectTimeout = null;
            }
            if (globalSock) {
                try {
                    globalSock.ev.removeAllListeners();
                    globalSock.ws?.close();
                    globalSock.end?.(undefined);
                } catch (_) {}
                globalSock = null;
            }
            isConnected = false;
            lastEmittedQr = null;
            if (fs.existsSync(authFolder)) {
                fs.rmSync(authFolder, { recursive: true, force: true });
            }
            sendStatus('whatsapp.status', 'disconnected');
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ status: 'ok', message: 'WhatsApp session reset, generating fresh QR...' }));
            scheduleReconnect(1500);
        } catch (err) {
            console.error("[Bridge] Failed to reset session:", err.message);
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: err.message }));
        }
    } else if (req.method === 'POST' && (url === '/pairing-code' || url.startsWith('/pairing-code'))) {
        let body = '';
        req.on('data', chunk => { body += chunk.toString(); });
        req.on('end', async () => {
            try {
                let targetNumber = OWNER_NUMBER.replace(/[^0-9]/g, '');
                if (body) {
                    try {
                        const parsed = JSON.parse(body);
                        if (parsed.phone_number) targetNumber = String(parsed.phone_number).replace(/[^0-9]/g, '');
                    } catch (_) {}
                }
                if (!targetNumber) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'Valid phone number is required' }));
                    return;
                }
                if (!globalSock || !globalSock.requestPairingCode) {
                    res.writeHead(503, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'WhatsApp socket not ready yet' }));
                    return;
                }
                console.log(`[Bridge] Generating pairing code on demand for: ${targetNumber}...`);
                const code = await globalSock.requestPairingCode(targetNumber);
                console.log(`[Bridge] Pairing code generated: ${code}`);
                await sendStatus('whatsapp.pairing_code', code);
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ status: 'ok', pairing_code: code }));
            } catch (err) {
                console.error("[Bridge] Error generating pairing code:", err);
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: err.message }));
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
