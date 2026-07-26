// JARVIS OS - HUD Logic

import { initThreeScene, setThinkingState, triggerAlert } from './three_scene.js';

const chatInput = document.getElementById('chat-input');
const chatHistory = document.getElementById('chat-history');
const mainStatus = document.getElementById('main-status');
const visionStatus = document.getElementById('vision-status');
const clockEl = document.getElementById('clock');
const sysLogs = document.getElementById('sys-logs');

// Clock
setInterval(() => {
  const now = new Date();
  clockEl.textContent = now.toLocaleTimeString('en-US', { hour12: false });
}, 1000);

// Fake telemetry updates to make UI feel alive
setInterval(() => {
  // Randomly adjust vision status bar
  const val = Math.floor(Math.random() * 100);
  visionStatus.style.width = `${val}%`;
}, 3000);

function addLog(msg) {
  const div = document.createElement('div');
  div.className = 'log-entry';
  div.textContent = msg;
  sysLogs.appendChild(div);
  sysLogs.scrollTop = sysLogs.scrollHeight;
}

function addMessage(text, isUser = false) {
  const div = document.createElement('div');
  div.className = `chat-message ${isUser ? 'user' : 'jarvis'}`;
  div.textContent = text;
  chatHistory.appendChild(div);
  chatHistory.scrollTop = chatHistory.scrollHeight;
}

chatInput.addEventListener('keypress', async (e) => {
  if (e.key === 'Enter' && chatInput.value.trim()) {
    const userText = chatInput.value.trim();
    addMessage(userText, true);
    chatInput.value = '';
    
    mainStatus.textContent = 'THINKING...';
    setThinkingState(true);
    addLog(`User command received: ${userText.substring(0, 20)}...`);

    try {
      // Connect to JARVIS Backend
      const response = await fetch('http://127.0.0.1:8000/api/chat', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-API-Key': 'JARVIS_DEV_KEY'
        },
        body: JSON.stringify({ message: userText, stream: false })
      });
      
      const data = await response.json();
      mainStatus.textContent = 'LISTENING';
      setThinkingState(false);
      
      if (data.content) {
        addMessage(data.content);
        addLog('Command executed successfully.');
      } else {
        addMessage('I encountered an error processing your request.', false);
      }
    } catch (err) {
      console.error(err);
      mainStatus.textContent = 'ERROR';
      setThinkingState(false);
      triggerAlert(true);
      addMessage('Connection to core systems lost.', false);
      addLog('ERR: Backend connection failed.');
      
      setTimeout(() => { 
        mainStatus.textContent = 'LISTENING'; 
        triggerAlert(false);
      }, 3000);
    }
  }
});

// Initialization & Telemetry
addLog('Establishing WebSocket connection to Core...');
initThreeScene('three-container');
const ws = new WebSocket('ws://127.0.0.1:8000/api/hud/ws?token=JARVIS_DEV_KEY');

ws.onopen = () => {
  addLog('WebSocket connected. Listening for telemetry...');
};

ws.onmessage = (event) => {
  try {
    const msg = JSON.parse(event.data);
    
    if (msg.type === 'system.ready') {
      addLog(`Core system ready. Tools loaded: ${msg.data.tools_registered}`);
    } else if (msg.type === 'hud.notification') {
      const { title, message, level } = msg.data;
      addLog(`[${level.toUpperCase()}] ${title}: ${message}`);
      
      // Flash the main status for severe alerts
      if (level === 'warning' || level === 'error') {
        triggerAlert(true);
        const oldStatus = mainStatus.textContent;
        mainStatus.textContent = `ALERT: ${title}`;
        mainStatus.style.color = '#ff4444';
        setTimeout(() => {
          mainStatus.textContent = oldStatus;
          mainStatus.style.color = '';
          triggerAlert(false);
        }, 5000);
      }
    }
  } catch (err) {
    console.error("Error parsing WS message:", err);
  }
};

ws.onclose = () => {
  addLog('WebSocket disconnected.');
};
