import { Capacitor } from '@capacitor/core';
import { DeviceHands } from '../lib/device-bridge';

// CompanionService.ts
// Connects to the Jarvis Backend via WebSocket to receive system commands.


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
  private intentionalDisconnect = false;
  private reconnectAttempts = 0;
  private maxReconnectDelay = 60000; // 60s cap
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
  private heartbeatTimeout: ReturnType<typeof setTimeout> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly HEARTBEAT_INTERVAL = 25000; // 25s — under typical 30s proxy timeout
  private readonly HEARTBEAT_TIMEOUT = 10000;  // 10s to receive pong

  constructor(backendUrl: string) {
    // If the url is http(s), convert it to ws(s)
    const url = new URL(backendUrl);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    url.pathname = '/api/ws/companion';
    this.backendUrl = url.toString();
  }

  public connect() {
    // Clean up any previous connection attempt
    this.cleanup();

    if (this.intentionalDisconnect) return;

    console.log('[Companion] Connecting to backend...', this.backendUrl);

    try {
      this.ws = new WebSocket(this.backendUrl);
    } catch (err) {
      console.error('[Companion] Failed to create WebSocket:', err);
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      console.log('[Companion] Connected to Jarvis Backend.');
      this.reconnectAttempts = 0; // Reset backoff on successful connection

      // Identify the device type to the backend
      let deviceType = 'web';
      const isTauriEnv = typeof window !== 'undefined' && ('__TAURI_INTERNALS__' in window || '__TAURI__' in window);
      if (isTauriEnv) {
        deviceType = 'pc';
      } else if (Capacitor.isNativePlatform()) {
        deviceType = 'mobile';
      }
      this.ws?.send(JSON.stringify({ type: 'register', device: deviceType }));

      // Start heartbeat keepalive
      this.startHeartbeat();
    };

    this.ws.onmessage = async (event) => {
      try {
        const data = JSON.parse(event.data);

        // Handle pong responses from the backend heartbeat
        if (data.type === 'pong') {
          this.clearHeartbeatTimeout();
          return;
        }

        const { action, task_id, params } = data;

        console.log(`[Companion] Received action: ${action}`, params);

        if (!action || !task_id) return;

        let result: any = { status: 'error', error: 'Unknown action' };
        const isTauri = typeof window !== 'undefined' && ('__TAURI_INTERNALS__' in window || '__TAURI__' in window);

        if (action === 'play_audio' || action === 'speak' || action === 'tts') {
          playAudio(params.audio_base64, params.format || 'mp3', params.text);
          result = { status: 'success' };
        } else if (isTauri) {
          // We are in Tauri Desktop Companion
          const invokeCmd = async (cmd: string, args: Record<string, any> = {}) => {
            try {
              const tauri = (window as any).__TAURI_INTERNALS__ || (window as any).__TAURI__?.core;
              if (tauri && typeof tauri.invoke === 'function') {
                return await tauri.invoke(cmd, args);
              }
              return { status: 'error', error: 'Tauri IPC bridge not available' };
            } catch (err: any) {
              return { status: 'error', error: err?.message || String(err) };
            }
          };

          if (action === 'run_command') {
            result = await invokeCmd('run_command', { command: params.command, cwd: params.cwd });
          } else if (action === 'open_app') {
            result = await invokeCmd('open_app', { appName: params.app_name, url: params.target_url });
          } else if (action === 'close_app') {
            result = await invokeCmd('close_app', { appName: params.app_name });
          } else if (action === 'show_notification') {
            result = await invokeCmd('show_notification', {
              title: params.title || 'Jarvis Notification',
              message: params.message || params.body || '',
            });
          } else if (action === 'capture_screen' || action === 'take_screenshot' || action === 'read_screen') {
            result = await invokeCmd('capture_screen');
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
          } else if (action === 'close_app') {
            try {
              let res: { success: boolean; message?: string; error?: string };
              try {
                res = await DeviceHands.closeApp({ name: params.app_name || 'current' });
              } catch (pluginErr: any) {
                const actionRes = await DeviceHands.performAction({ action: 'close_app', target: params.app_name || 'current' });
                res = {
                  success: actionRes.success,
                  message: actionRes.message || (actionRes.success ? `Closed app: ${params.app_name}` : `Failed to close ${params.app_name}`)
                };
              }
              result = { status: res.success ? 'success' : 'error', output: res.message || res.error || 'Closed app.' };
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
          } else if (action === 'type_text' || action === 'type') {
            try {
              const res = await DeviceHands.performAction({
                action: 'type_text',
                text: params.text || params.target || ''
              });
              result = { status: res.success ? 'success' : 'error', output: res.message || 'Typed text.' };
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
          } else if (action === 'back' || action === 'home' || action === 'recents') {
            try {
              const res = await DeviceHands.performAction({ action });
              result = { status: res.success ? 'success' : 'error', output: `Performed ${action}.` };
            } catch (err: any) {
              result = { status: 'error', error: err.message || String(err) };
            }
          } else if (action === 'read_screen') {
            try {
              const screenData = await DeviceHands.readScreen();
              result = { status: 'success', output: screenData.elements };
            } catch (err: any) {
              result = { status: 'error', error: err.message || String(err) };
            }
          } else if (action === 'get_battery') {
            try {
              const bRes = await DeviceHands.getBattery();
              result = { status: 'success', output: bRes.output || `Battery level: ${bRes.level}%, Charging: ${bRes.charging}` };
            } catch (err: any) {
              if ('getBattery' in navigator) {
                try {
                  const battery: any = await (navigator as any).getBattery();
                  result = {
                    status: 'success',
                    output: `Battery level: ${Math.round(battery.level * 100)}%, Charging: ${battery.charging}`
                  };
                } catch {
                  result = { status: 'error', error: err.message || String(err) };
                }
              } else {
                result = { status: 'error', error: err.message || String(err) };
              }
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
          } else if (action === 'send_sms') {
            try {
              const res = await DeviceHands.sendSMS({ number: params.number, message: params.message });
              result = { status: res.success ? 'success' : 'error', output: res.message || 'SMS sent.' };
            } catch (err: any) {
              result = { status: 'error', error: err.message || String(err) };
            }
          } else if (action === 'make_call') {
            try {
              const res = await DeviceHands.makeCall({ number: params.number });
              result = { status: res.success ? 'success' : 'error', output: res.message || 'Call initiated.' };
            } catch (err: any) {
              result = { status: 'error', error: err.message || String(err) };
            }
          } else if (action === 'show_notification') {
            try {
              await DeviceHands.showNotification({ title: params.title || 'Jarvis', message: params.message || '' });
              result = { status: 'success', output: 'Notification displayed.' };
            } catch {
              if ('Notification' in window && Notification.permission === 'granted') {
                new Notification(params.title || 'Jarvis Alert', { body: params.message || params.body || '' });
                result = { status: 'success' };
              } else {
                result = { status: 'success', output: 'Notification received.' };
              }
            }
          } else {
            result = { status: 'error', error: `Action '${action}' not supported on mobile companion.` };
          }
        } else {
          // We are in a standard browser
          if (action === 'show_notification' && 'Notification' in window && Notification.permission === 'granted') {
            new Notification(params.title || 'Jarvis Alert', { body: params.message || params.body || '' });
            result = { status: 'success' };
          } else {
            result = { status: 'error', error: 'Companion commands only supported on Desktop (Tauri) or Native Mobile (Capacitor).' };
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
      console.log('[Companion] Disconnected.');
      this.stopHeartbeat();
      if (!this.intentionalDisconnect) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = (err) => {
      console.error('[Companion] WebSocket error:', err);
      // onclose will fire after onerror, triggering reconnect
    };
  }

  /** Heartbeat keepalive: sends ping, expects pong within timeout */
  private startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
        // Set a timeout — if we don't get pong, force reconnect
        this.heartbeatTimeout = setTimeout(() => {
          console.warn('[Companion] Heartbeat timeout — no pong received. Forcing reconnect.');
          this.ws?.close();
        }, this.HEARTBEAT_TIMEOUT);
      }
    }, this.HEARTBEAT_INTERVAL);
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
    this.clearHeartbeatTimeout();
  }

  private clearHeartbeatTimeout() {
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = null;
    }
  }

  /** Exponential backoff reconnect: 1s, 2s, 4s, 8s, ... up to 60s */
  private scheduleReconnect() {
    if (this.intentionalDisconnect) return;

    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), this.maxReconnectDelay);
    this.reconnectAttempts++;
    console.log(`[Companion] Reconnecting in ${Math.round(delay / 1000)}s (attempt ${this.reconnectAttempts})...`);

    this.reconnectTimer = setTimeout(() => this.connect(), delay);
  }

  /** Clean up WebSocket and all timers without triggering auto-reconnect */
  private cleanup() {
    this.stopHeartbeat();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onclose = null;
      this.ws.onerror = null;
      if (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING) {
        this.ws.close();
      }
      this.ws = null;
    }
  }

  /**
   * Called by the visibility change handler when the page comes back to the foreground.
   * Forces an immediate reconnect if the WebSocket is not currently open.
   */
  public reconnectIfNeeded() {
    if (this.intentionalDisconnect) return;
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.log('[Companion] App resumed — reconnecting immediately.');
      this.reconnectAttempts = 0; // Reset backoff for immediate reconnect
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
      this.connect();
    }
  }

  public disconnect() {
    this.intentionalDisconnect = true;
    this.cleanup();
  }
}
