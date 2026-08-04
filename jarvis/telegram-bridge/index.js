require('dotenv').config({ path: '../../.env' });
const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');

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

const JARVIS_EVENT_URL = 'http://127.0.0.1:8000/api/telegram/event';

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

async function connectToTelegram() {
    console.log('[Bridge] Starting Jarvis Telegram Bridge...');

    const bot = new TelegramBot(BOT_TOKEN, { polling: true });

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
        await sendStatus('telegram.status', 'polling_error');
    });

    // Handle incoming messages
    bot.on('message', async (msg) => {
        const chatId = msg.chat.id;
        const senderId = msg.from.id.toString();
        const text = msg.text;

        console.log(`\n[DEBUG] Message received from: ${senderId} (chat: ${chatId})`);

        // Security: only respond to the owner
        if (senderId !== OWNER_ID) {
            console.log(`[Security] Ignored message from unauthorized user: ${senderId}`);
            return;
        }

        // Must have text content
        if (!text) return;

        // Check if the trigger word "jarvis" is present
        if (!text.toLowerCase().includes('jarvis')) {
            return;
        }

        console.log(`\n[Owner] ${text}`);

        // Send typing indicator
        await bot.sendChatAction(chatId, 'typing');

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

            if (!reply.startsWith('[Jarvis]: ')) {
                reply = `[Jarvis]: ${reply}`;
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

connectToTelegram();
