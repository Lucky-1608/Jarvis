import { Capacitor } from '@capacitor/core';
import { DeviceHands } from '../lib/device-bridge';

// CompanionService.ts
// Connects to the Jarvis Backend via WebSocket to receive system commands.

declare global {
  interface Window {
    electronAPI?: {
      runCommand: (command: string, cwd?: string) => Promise<{ status: string, output?: any, error?: string }>;
      openApp: (appName: string, url?: string) => Promise<{ status: string, error?: string }>;
    };
  }
}

export class CompanionService {
  private ws: WebSocket | null = null;
  private backendUrl: string;

  constructor(backendUrl: string) {
    // If the url is http(s), convert it to ws(s)
    const url = new URL(backendUrl);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    url.pathname = '/api/ws/companion';
    this.backendUrl = url.toString();
  }

  public connect() {
    console.log('[Companion] Connecting to backend...', this.backendUrl);
    this.ws = new WebSocket(this.backendUrl);

    this.ws.onopen = () => {
      console.log('[Companion] Connected to Jarvis Backend.');
    };


    this.ws.onmessage = async (event) => {
      try {
        const data = JSON.parse(event.data);
        const { action, task_id, params } = data;

        console.log(`[Companion] Received action: ${action}`, params);

        if (!action || !task_id) return;

        let result: any = { status: 'error', error: 'Unknown action' };

        if (window.electronAPI) {
          // We are in Electron
          if (action === 'run_command') {
            result = await window.electronAPI.runCommand(params.command, params.cwd);
          } else if (action === 'open_app') {
            result = await window.electronAPI.openApp(params.app_name, params.target_url);
          }
        } else if (Capacitor.isNativePlatform()) {
          // We are on Mobile (Android/iOS)
          if (action === 'open_app') {
            try {
              const res = await DeviceHands.launchApp({ name: params.app_name });
              result = { status: res.success ? 'success' : 'error', output: res.message || res.error || 'Launched app.' };
            } catch (err: any) {
              result = { status: 'error', error: err.message || String(err) };
            }
          } else {
             result = { status: 'error', error: 'Action not supported on mobile companion.' };
          }
        } else {
          // We are in a standard browser
          result = { status: 'error', error: 'Companion commands only supported on Desktop (Electron) or Native Mobile (Capacitor).' };
        }

        // Send the result back
        const response = {
          task_id,
          ...result
        };
        
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify(response));
        }

      } catch (e) {
        console.error('[Companion] Error processing message:', e);
      }
    };

    this.ws.onclose = () => {
      console.log('[Companion] Disconnected. Reconnecting in 5s...');
      setTimeout(() => this.connect(), 5000);
    };

    this.ws.onerror = (err) => {
      console.error('[Companion] WebSocket error:', err);
      this.ws?.close();
    };
  }

  public disconnect() {
    if (this.ws) {
      this.ws.onclose = null; // Prevent auto-reconnect
      this.ws.close();
      this.ws = null;
    }
  }
}
