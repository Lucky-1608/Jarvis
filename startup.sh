#!/bin/bash
# startup.sh - Custom startup script for Python Web Apps that need Node.js

echo "Starting custom initialization..."

# 1. Download and extract Node.js locally (since we might not have root access to use apt-get)
NODE_VERSION="v20.15.1"
NODE_DIST="node-${NODE_VERSION}-linux-x64"

if [ ! -f "/tmp/node-bin/bin/npm" ]; then
    echo "Downloading Node.js..."
    rm -rf /tmp/node-bin
    curl -O https://nodejs.org/dist/${NODE_VERSION}/${NODE_DIST}.tar.xz
    tar -xf ${NODE_DIST}.tar.xz
    mkdir -p /tmp/node-bin
    cp -r ${NODE_DIST}/* /tmp/node-bin/
    rm -rf ${NODE_DIST} ${NODE_DIST}.tar.xz
    echo "Node.js downloaded and extracted."
fi

# 2. Add our local Node.js to the system PATH so Python's subprocess can find it
export PATH=/tmp/node-bin/bin:$PATH

echo "Node version: $(node -v)"
echo "NPM version: $(npm -v)"

# 3. Install the bridge dependencies
echo "Installing WhatsApp bridge dependencies..."
cd jarvis/whatsapp-bridge && npm install
cd ../..

echo "Installing Telegram bridge dependencies..."
cd jarvis/telegram-bridge && npm install
cd ../..

# 4. Start the Python FastAPI backend
echo "Starting Jarvis Backend..."
python -m uvicorn jarvis.server.app:app --host 0.0.0.0 --port 8000
