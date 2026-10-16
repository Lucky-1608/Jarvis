import { Capacitor } from '@capacitor/core';
import { DeviceHands } from '../lib/device-bridge';

// CompanionService.ts
// Connects to the Jarvis Backend via WebSocket to receive system commands.

declare global {
  interface Window {
    electronAPI?: {
      runCommand: (command: string, cwd?: string) => Promise<{ status: string, output?: any, error?: string }>;
      openApp: (appName: string, url?: string) => Promise<{ status: string, error?: string }>;
      closeApp: (appName: string) => Promise<{ status: string, error?: string }>;
      openExternal?: (url: string) => Promise<{ status: string, error?: string }>;
      showNotification: (title: string, body: string) => Promise<{ status: string, error?: string }>;
      captureScreen: () => Promise<{ status: string, image_base64?: string, error?: string }>;
    };
  }
}

function playAudio(audioBase64?: string, format: string = 'mp3', textFallback?: string) {
  if (audioBase64) {
    const mime = (format === 'mp3' || format === 'mpeg') ? 'audio/mpeg' : `audio/${format}`;
    const audio = new Audio(`data:${mime};base64,${audioBase64}`);
    audio.play().catch((err) => {
      console.warn('[Companion] Audio playback blocked, trying SpeechSynthesis fallback:', err);
      if (textFallback && typeof window !== 'undefined' && 'speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(textFallback);
        window.speechSynthesis.speak(utterance);
      }
    });
  } else if (textFallback && typeof window !== 'undefined' && 'speechSynthesis' in window) {
    const utterance = new SpeechSynthesisUtterance(textFallback);
    window.speechSynthesis.speak(utterance);
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
      // Identify the device type to the backend
      let deviceType = 'web';
      if (window.electronAPI) {
        deviceType = 'pc';
      } else if (Capacitor.isNativePlatform()) {
        deviceType = 'mobile';
      }
      this.ws?.send(JSON.stringify({ type: 'register', device: deviceType }));
    };

    this.ws.onmessage = async (event) => {
      try {
        const data = JSON.parse(event.data);
        const { action, task_id, params } = data;

        console.log(`[Companion] Received action: ${action}`, params);

        if (!action || !task_id) return;

        let result: any = { status: 'error', error: 'Unknown action' };

        if (action === 'play_audio' || action === 'speak' || action === 'tts') {
          playAudio(params.audio_base64, params.format || 'mp3', params.text);
          result = { status: 'success' };
        } else if (window.electronAPI) {
          // We are in Electron Desktop Companion
          if (action === 'run_command') {
            result = await window.electronAPI.runCommand(params.command, params.cwd);
          } else if (action === 'open_app') {
            result = await window.electronAPI.openApp(params.app_name, params.target_url);
          } else if (action === 'close_app') {
            result = await window.electronAPI.closeApp(params.app_name);
          } else if (action === 'show_notification') {
            result = await window.electronAPI.showNotification(
              params.title || 'Jarvis Notification',
              params.message || params.body || ''
            );
          } else if (action === 'capture_screen' || action === 'take_screenshot' || action === 'read_screen') {
            result = await window.electronAPI.captureScreen();
          }
        } else if (Capacitor.isNativePlatform()) {
          // We are on Mobile (Android/iOS)
          if (action === 'open_app') {
            try {
              let res: { success: boolean; message?: string; error?: string };
              try {
                res = await DeviceHands.launchApp({ name: params.app_name });
              } catch (pluginErr: any) {
                const errMsg = pluginErr?.message || String(pluginErr);
                if (errMsg.includes('not implemented') || errMsg.includes('launchApp')) {
                  console.log('[Companion] DeviceHands.launchApp not implemented, falling back to performAction');
                  const actionRes = await DeviceHands.performAction({ action: 'open_app', target: params.app_name });
                  res = {
                    success: actionRes.success,
                    message: actionRes.message || (actionRes.success ? `Opened app: ${params.app_name}` : `Failed to open ${params.app_name}`)
                  };
                } else {
                  throw pluginErr;
                }
              }
              result = { status: res.success ? 'success' : 'error', output: res.message || res.error || 'Launched app.' };
            } catch (err: any) {
              result = { status: 'error', error: err.message || String(err) };
            }
          } else if (action === 'tap') {
            try {
              const res = await DeviceHands.performAction({
                action: 'tap',
                target: params.target || '',
                x: params.x,
                y: params.y
              });
              result = { status: res.success ? 'success' : 'error', output: res.message || 'Tapped element.' };
            } catch (err: any) {
              result = { status: 'error', error: err.message || String(err) };
            }
          } else if (action === 'scroll') {
            try {
              const res = await DeviceHands.performAction({
                action: 'scroll',
                target: params.direction || 'down'
              });
              result = { status: res.success ? 'success' : 'error', output: res.message || 'Scrolled.' };
            } catch (err: any) {
              result = { status: 'error', error: err.message || String(err) };
            }
          } else if (action === 'read_screen') {
            try {
              if (DeviceHands.readScreen) {
                const screenData = await DeviceHands.readScreen();
                result = { status: 'success', output: screenData.elements };
              } else {
                result = { status: 'error', error: 'readScreen not supported by this build.' };
              }
            } catch (err: any) {
              result = { status: 'error', error: err.message || String(err) };
            }
          } else if (action === 'get_battery') {
            try {
              if ('getBattery' in navigator) {
                const battery: any = await (navigator as any).getBattery();
                result = {
                  status: 'success',
                  output: `Battery level: ${Math.round(battery.level * 100)}%, Charging: ${battery.charging}`
                };
              } else {
                result = { status: 'success', output: 'Battery status unavailable.' };
              }
            } catch (err: any) {
              result = { status: 'error', error: err.message || String(err) };
            }
          } else if (action === 'get_location') {
            try {
              const pos: GeolocationPosition = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 10000 });
              });
              result = {
                status: 'success',
                output: `Latitude: ${pos.coords.latitude}, Longitude: ${pos.coords.longitude}, Accuracy: ${pos.coords.accuracy}m`
              };
            } catch (err: any) {
              result = { status: 'error', error: err.message || String(err) };
            }
          } else if (action === 'show_notification') {
            // Standard browser/Capacitor notification fallback
            if ('Notification' in window && Notification.permission === 'granted') {
              new Notification(params.title || 'Jarvis Alert', { body: params.message || params.body || '' });
              result = { status: 'success' };
            } else {
              result = { status: 'success', output: 'Notification received.' };
            }
          } else {
             result = { status: 'error', error: 'Action not supported on mobile companion.' };
          }
        } else {
          // We are in a standard browser
          if (action === 'show_notification' && 'Notification' in window && Notification.permission === 'granted') {
            new Notification(params.title || 'Jarvis Alert', { body: params.message || params.body || '' });
            result = { status: 'success' };
          } else {
            result = { status: 'error', error: 'Companion commands only supported on Desktop (Electron) or Native Mobile (Capacitor).' };
          }
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
