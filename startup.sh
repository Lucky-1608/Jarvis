#!/bin/bash
# startup.sh - Custom startup script for Python Web Apps that need Node.js

echo "Starting custom initialization..."

# 1. Download and extract Node.js locally
NODE_VERSION="v20.15.1"
NODE_DIST="node-${NODE_VERSION}-linux-x64"

if [ ! -f "/tmp/node-bin/bin/npm" ]; then
    echo "Downloading Node.js..."
    rm -rf /tmp/node-bin
    curl -s -O https://nodejs.org/dist/${NODE_VERSION}/${NODE_DIST}.tar.xz
    tar -xf ${NODE_DIST}.tar.xz
    mkdir -p /tmp/node-bin
    cp -r ${NODE_DIST}/* /tmp/node-bin/
    rm -rf ${NODE_DIST} ${NODE_DIST}.tar.xz
    echo "Node.js downloaded and extracted."
fi

# 2. Add our local Node.js to the system PATH
export PATH=/tmp/node-bin/bin:$PATH

echo "Node version: $(node -v)"
echo "NPM version: $(npm -v)"

# 3. Install the bridge dependencies persistently (only if missing)
echo "Setting up WhatsApp bridge dependencies..."
cd jarvis/whatsapp-bridge
mkdir -p /home/site/whatsapp_bridge_cache
if ! cmp -s package.json /home/site/whatsapp_bridge_cache/package.json; then
    echo "Running npm install for WhatsApp bridge..."
    cp package.json /home/site/whatsapp_bridge_cache/
    [ -f package-lock.json ] && cp package-lock.json /home/site/whatsapp_bridge_cache/
    npm install --prefix /home/site/whatsapp_bridge_cache --no-audit --no-fund
else
    echo "WhatsApp dependencies already installed and up to date."
fi
rm -rf node_modules
ln -s /home/site/whatsapp_bridge_cache/node_modules node_modules
cd ../..

echo "Setting up Telegram bridge dependencies..."
cd jarvis/telegram-bridge
mkdir -p /home/site/telegram_bridge_cache
if ! cmp -s package.json /home/site/telegram_bridge_cache/package.json; then
    echo "Running npm install for Telegram bridge..."
    cp package.json /home/site/telegram_bridge_cache/
    [ -f package-lock.json ] && cp package-lock.json /home/site/telegram_bridge_cache/
    npm install --prefix /home/site/telegram_bridge_cache --no-audit --no-fund
else
    echo "Telegram dependencies already installed and up to date."
fi
rm -rf node_modules
ln -s /home/site/telegram_bridge_cache/node_modules node_modules
cd ../..

# Note: Bridges are now started by jarvis/server/app.py during the lifespan event
# to ensure they start only after the FastAPI backend is ready to receive events.

# 5. Start the Python FastAPI backend
echo "Starting Jarvis Backend..."
# Use $PORT environment variable if Azure provides it, otherwise default to 8000
PORT="${PORT:-8000}"
BIND_HOST="${JARVIS_HOST:-0.0.0.0}"
if [ "$BIND_HOST" != "127.0.0.1" ] && [ "$BIND_HOST" != "localhost" ] && [ "$BIND_HOST" != "::1" ]; then
    if [ -z "${JARVIS_SECRET_KEY:-}" ] || [ "$JARVIS_SECRET_KEY" = "replace-with-a-long-random-secret" ] || [ "$JARVIS_SECRET_KEY" = "change-this-to-a-random-secret" ]; then
        echo "JARVIS_SECRET_KEY must be a unique secret when binding beyond loopback."
        exit 1
    fi
    export JARVIS_REQUIRE_AUTH=true
fi
export JARVIS_BIND_HOST="$BIND_HOST"
python -m uvicorn jarvis.server.app:app --host "$BIND_HOST" --port "$PORT" --proxy-headers --forwarded-allow-ips="*"


