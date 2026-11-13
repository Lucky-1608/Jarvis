/**
 * Jarvis OS — Automatic Update Service.
 *
 * Checks for mandatory/optional application updates on startup and periodically.
 * Shows native desktop notifications when updates are detected, and coordinates
 * mandatory update enforcement and installer execution.
 */

import { useUpdateStore } from '../store/updateStore';
import { getBaseUrl } from '../lib/api';
import { Capacitor } from '@capacitor/core';
import { DeviceHands } from '../lib/device-bridge';

// Platform detection
export function getClientPlatform(): 'windows' | 'android' | 'ios' | 'web' {
  if (typeof window !== 'undefined' && Capacitor.isNativePlatform()) {
    const plat = Capacitor.getPlatform();
    if (plat === 'android') return 'android';
    if (plat === 'ios') return 'ios';
  }
  if (isTauriEnvironment()) {
    return 'windows';
  }
  return 'web';
}

// Safe Tauri invocation helper
export function isTauriEnvironment(): boolean {
  return (
    typeof window !== 'undefined' &&
    ('__TAURI_INTERNALS__' in window ||
      '__TAURI__' in window ||
      window.location.protocol.startsWith('tauri') ||
      window.location.protocol === 'file:')
  );
}

export async function invokeTauri<T = any>(command: string, args: Record<string, any> = {}): Promise<T | null> {
  if (!isTauriEnvironment()) return null;
  try {
    const tauriCore = await import('@tauri-apps/api/core');
    return await tauriCore.invoke<T>(command, args);
  } catch (err) {
    console.warn(`[UpdateService] Tauri invoke failed for '${command}':`, err);
    return null;
  }
}

/**
 * Triggers native OS notification (via Tauri or Web Notifications API).
 */
export async function showUpdateNotification(title: string, message: string) {
  // 1. Try mobile native notification (Android / Capacitor)
  if (typeof window !== 'undefined' && Capacitor.isNativePlatform()) {
    try {
      await DeviceHands.showNotification({ title, message });
      return;
    } catch (e) {}
  }

  // 2. Try Tauri native notification
  if (isTauriEnvironment()) {
    try {
      await invokeTauri('show_notification', { title, message });
      return;
    } catch (e) {
      // Fall through to browser notification
    }
  }

  // 2. Fall back to Web Notification API
  if (typeof window !== 'undefined' && 'Notification' in window) {
    if (Notification.permission === 'granted') {
      try {
        new Notification(title, { body: message, icon: '/favicon.svg' });
      } catch (e) {}
    } else if (Notification.permission !== 'denied') {
      try {
        const permission = await Notification.requestPermission();
        if (permission === 'granted') {
          new Notification(title, { body: message, icon: '/favicon.svg' });
        }
      } catch (e) {}
    }
  }
}

/**
 * Retrieve current client app version.
 */
export async function getClientAppVersion(): Promise<string> {
  if (isTauriEnvironment()) {
    try {
      const res = await invokeTauri<{ status: string; version: string }>('get_app_version');
      if (res?.version) {
        return res.version;
      }
    } catch (e) {}
  }
  return '1.0.0';
}

/**
 * Compare two semver-like strings (e.g. "1.0.1" > "1.0.0").
 */
function isVersionNewer(latest: string, current: string): boolean {
  const parse = (v: string) =>
    v
      .replace(/^[^\d]*/, '')
      .split('.')
      .map((n) => parseInt(n, 10) || 0);

  const lParts = parse(latest);
  const cParts = parse(current);

  const len = Math.max(lParts.length, cParts.length);
  for (let i = 0; i < len; i++) {
    const l = lParts[i] || 0;
    const c = cParts[i] || 0;
    if (l > c) return true;
    if (l < c) return false;
  }
  return false;
}

export class UpdateService {
  private static checkIntervalId: any = null;

  /**
   * Run update check against backend or GitHub Releases.
   */
  static async checkForUpdates(silent: boolean = false): Promise<boolean> {
    const store = useUpdateStore.getState();
    store.setUpdateInfo({ isChecking: true, error: null });

    const currentVersion = await getClientAppVersion();
    const platform = getClientPlatform();
    store.setUpdateInfo({ currentVersion });

    try {
      let data: any = null;
      const baseUrl = await getBaseUrl();

      // 1. Try querying Jarvis Backend API
      if (baseUrl) {
        try {
          const resp = await fetch(
            `${baseUrl}/api/updates/check?current_version=${encodeURIComponent(currentVersion)}&platform=${platform}`,
            {
              method: 'GET',
              headers: { Accept: 'application/json' },
            }
          );
          if (resp.ok) {
            data = await resp.json();
          }
        } catch (fetchErr) {
          console.debug('[UpdateService] Backend update check offline, checking GitHub fallback...', fetchErr);
        }
      }

      // 2. Direct GitHub Releases fallback if backend is unreachable or returned nothing
      if (!data) {
        try {
          const ghResp = await fetch('https://api.github.com/repos/Lucky-1608/Jarvis/releases/latest', {
            headers: { Accept: 'application/vnd.github.v3+json' },
          });
          if (ghResp.ok) {
            const release = await ghResp.json();
            const tag = release.tag_name || '';
            const latestVer = tag.replace(/^v/, '');
            const newer = isVersionNewer(latestVer, currentVersion);

            let assetUrl = release.html_url || 'https://github.com/Lucky-1608/Jarvis/releases/latest';
            if (Array.isArray(release.assets)) {
              if (platform === 'android') {
                const apkAsset = release.assets.find((a: any) =>
                  a.name?.toLowerCase().endsWith('.apk')
                );
                if (apkAsset?.browser_download_url) assetUrl = apkAsset.browser_download_url;
              } else {
                const exeAsset = release.assets.find((a: any) =>
                  a.name?.toLowerCase().endsWith('.exe')
                );
                if (exeAsset?.browser_download_url) assetUrl = exeAsset.browser_download_url;
              }
            }

            data = {
              update_available: newer,
              mandatory: newer,
              current_version: currentVersion,
              latest_version: latestVer,
              title: release.name || `Jarvis OS v${latestVer} Update`,
              release_notes: release.body || 'Frontend enhancements and core system updates.',
              download_url: assetUrl,
              published_at: release.published_at,
            };
          }
        } catch (ghErr) {
          console.debug('[UpdateService] GitHub release fetch failed:', ghErr);
        }
      }

      if (data) {
        const updateAvailable = !!data.update_available;
        const mandatory = !!data.mandatory;

        store.setUpdateInfo({
          isChecking: false,
          updateAvailable,
          mandatory,
          latestVersion: data.latest_version || currentVersion,
          title: data.title || 'Jarvis OS Update Required',
          releaseNotes: data.release_notes || 'Frontend and core application updates.',
          downloadUrl: data.download_url || 'https://github.com/Lucky-1608/Jarvis/releases/latest',
          publishedAt: data.published_at || null,
          lastChecked: Date.now(),
        });

        if (updateAvailable) {
          showUpdateNotification(
            '⚡ Jarvis Update Required',
            `Version v${data.latest_version} has been released. You must update Jarvis to continue.`
          );
        }

        return updateAvailable;
      }

      store.setUpdateInfo({ isChecking: false, lastChecked: Date.now() });
      return false;
    } catch (err: any) {
      console.error('[UpdateService] Update check failed:', err);
      store.setUpdateInfo({
        isChecking: false,
        error: err.message || 'Failed to check for updates',
        lastChecked: Date.now(),
      });
      return false;
    }
  }

  /**
   * Instantly switch / sync the live frontend from Azure without reinstalling anything.
   */
  static async syncLiveFrontend(): Promise<void> {
    const store = useUpdateStore.getState();
    store.setIsUpdating(true);
    store.setUpdateStatusText('Synchronizing latest live frontend...');

    if (isTauriEnvironment()) {
      try {
        await invokeTauri('sync_latest_frontend');
        store.setUpdateStatusText('Live frontend synchronized!');
        setTimeout(() => {
          store.reset();
        }, 1200);
        return;
      } catch (err) {
        console.warn('Tauri live sync error, falling back to window location:', err);
      }
    }

    // Web / mobile / fallback:
    window.location.href = 'https://jarvisos-gdhfgnc4gscqecav.centralindia-01.azurewebsites.net';
  }

  /**
   * Start installer download and restart app.
   */
  static async startUpdateInstallation(): Promise<void> {
    const store = useUpdateStore.getState();
    const downloadUrl = store.downloadUrl || 'https://github.com/Lucky-1608/Jarvis/releases/latest';

    store.setIsUpdating(true);
    store.setUpdateStatusText('Downloading latest Jarvis installer and preparing update...');

    // 1. Android Native In-App Self-Update
    if (typeof window !== 'undefined' && Capacitor.isNativePlatform() && Capacitor.getPlatform() === 'android') {
      try {
        store.setUpdateStatusText('Downloading APK update in background...');
        await DeviceHands.installApk({ url: downloadUrl });
        store.setUpdateStatusText('Launching Android Package Installer...');
        setTimeout(() => {
          store.setIsUpdating(false);
          store.setUpdateStatusText(null);
        }, 3500);
        return;
      } catch (err: any) {
        console.error('[UpdateService] In-App APK install failed, falling back to browser download:', err);
      }
    }

    // 2. Windows Native Tauri Self-Update
    if (isTauriEnvironment()) {
      try {
        const result = await invokeTauri('install_update_and_restart', { downloadUrl });
        store.setUpdateStatusText('Installer launched. Closing Jarvis to apply update...');
        // Wait briefly for the detached installer process to spin up
        setTimeout(() => {
          invokeTauri('exit_app');
        }, 2000);
        return;
      } catch (err: any) {
        console.error('[UpdateService] Automatic installer launch failed, opening browser:', err);
      }
    }

    // Web or fallback: open the download link
    store.setUpdateStatusText('Opening download link...');
    window.open(downloadUrl, '_blank');
    setTimeout(() => {
      store.setIsUpdating(false);
      store.setUpdateStatusText(null);
    }, 2500);
  }

  /**
   * Quit the application.
   */
  static async quitApplication(): Promise<void> {
    if (isTauriEnvironment()) {
      await invokeTauri('exit_app');
    } else {
      window.close();
    }
  }

  /**
   * Start auto-polling for updates on startup, visibility change, and interval.
   */
  static initialize() {
    // 1. Initial check after 2 seconds
    setTimeout(() => {
      UpdateService.checkForUpdates(true);
    }, 2000);

    // 2. Poll every 10 minutes
    if (this.checkIntervalId) {
      clearInterval(this.checkIntervalId);
    }
    this.checkIntervalId = setInterval(() => {
      UpdateService.checkForUpdates(true);
    }, 10 * 60 * 1000);

    // 3. Check whenever the window regains focus or visibility
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
          const store = useUpdateStore.getState();
          // Check if at least 2 minutes passed since last check
          if (!store.lastChecked || Date.now() - store.lastChecked > 2 * 60 * 1000) {
            UpdateService.checkForUpdates(true);
          }
        }
      });
    }
  }
}

