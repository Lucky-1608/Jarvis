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

# 4. Start the Python FastAPI backend
echo "Starting Jarvis Backend..."
# Use $PORT environment variable if Azure provides it, otherwise default to 8000
PORT="${PORT:-8000}"
python -m uvicorn jarvis.server.app:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"
