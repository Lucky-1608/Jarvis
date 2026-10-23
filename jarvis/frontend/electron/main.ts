import {
  app,
  BrowserWindow,
  ipcMain,
  shell,
  Tray,
  Menu,
  nativeImage,
  type NativeImage,
  globalShortcut,
  Notification,
  desktopCapturer,
} from 'electron';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { exec } from 'node:child_process';
import util from 'node:util';

const execAsync = util.promisify(exec);

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// The built directory structure
//
// ├─┬─┬ dist
// │ │ └── index.html
// │ │
// │ ├─┬ dist-electron
// │ │ ├── main.js
// │ │ └── preload.js
// │
process.env.APP_ROOT = path.join(__dirname, '..');

export const VITE_DEV_SERVER_URL = process.env['VITE_DEV_SERVER_URL'];
export const MAIN_DIST = path.join(process.env.APP_ROOT, 'dist-electron');
export const RENDERER_DIST = path.join(process.env.APP_ROOT, 'dist');

process.env.VITE_PUBLIC = VITE_DEV_SERVER_URL ? path.join(process.env.APP_ROOT, 'public') : RENDERER_DIST;

let win: BrowserWindow | null = null;
let tray: Tray | null = null;
let isQuitting = false;
let hasShownTrayBalloon = false;

function resolveIconPath(): string | null {
  const candidatePaths = [
    path.join(process.env.VITE_PUBLIC || '', 'arc_reactor.png'),
    path.join(__dirname, '../public/arc_reactor.png'),
    path.join(__dirname, '../dist/arc_reactor.png'),
    path.join(process.cwd(), 'public/arc_reactor.png'),
    path.join(process.cwd(), 'dist/arc_reactor.png'),
    path.join(process.cwd(), 'jarvis/frontend/public/arc_reactor.png'),
    path.join(process.cwd(), 'jarvis/frontend/dist/arc_reactor.png'),
    path.join(app.getAppPath(), 'public/arc_reactor.png'),
    path.join(app.getAppPath(), 'dist/arc_reactor.png'),
  ];

  for (const p of candidatePaths) {
    try {
      if (fs.existsSync(p)) {
        return p;
      }
    } catch {
      // Ignore errors for unreadable paths
    }
  }
  return null;
}

function getAppIcon(): NativeImage {
  const resolved = resolveIconPath();
  if (resolved) {
    try {
      const img = nativeImage.createFromPath(resolved);
      if (!img.isEmpty()) {
        return img;
      }
    } catch (e) {
      console.warn('Failed to load icon from path:', resolved, e);
    }
  }

  // Fallback high-contrast Arc Reactor SVG rendered as DataURL
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
    <circle cx="32" cy="32" r="28" fill="#030712" stroke="#00d8ff" stroke-width="4"/>
    <circle cx="32" cy="32" r="16" fill="#00d8ff" fill-opacity="0.4" stroke="#38bdf8" stroke-width="3"/>
    <circle cx="32" cy="32" r="6" fill="#ffffff"/>
  </svg>`;
  return nativeImage.createFromDataURL(`data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}`);
}

function getTrayIcon(): NativeImage {
  const icon = getAppIcon();
  // Windows System Tray requires 16x16 or 32x32 pixels
  return icon.resize({ width: 16, height: 16 });
}

function createTray() {
  if (tray) return;

  try {
    const icon = getTrayIcon();
    tray = new Tray(icon);
    tray.setToolTip('Jarvis Companion OS');

    const contextMenu = Menu.buildFromTemplate([
      {
        label: 'Open Jarvis',
        click: () => {
          if (win) {
            win.show();
            win.focus();
          }
        },
      },
      {
        label: 'Minimize to Tray',
        click: () => {
          win?.hide();
        },
      },
      { type: 'separator' },
      {
        label: 'Shortcut: Ctrl+Shift+J / Cmd+Shift+J',
        enabled: false,
      },
      { type: 'separator' },
      {
        label: 'Quit Jarvis',
        click: () => {
          isQuitting = true;
          app.quit();
        },
      },
    ]);

    tray.setContextMenu(contextMenu);

    tray.on('click', () => {
      if (win) {
        if (win.isVisible() && !win.isMinimized()) {
          win.hide();
        } else {
          win.show();
          win.focus();
        }
      }
    });

    tray.on('double-click', () => {
      if (win) {
        win.show();
        win.focus();
      }
    });
  } catch (err) {
    console.error('Failed to initialize system tray:', err);
  }
}

function createWindow() {
  const appIcon = getAppIcon();

  win = new BrowserWindow({
    width: 1200,
    height: 800,
    icon: appIcon,
    webPreferences: {
      preload: path.join(__dirname, 'preload.mjs'),
      nodeIntegration: false,
      contextIsolation: true,
      backgroundThrottling: false, // Ensure background tasks/WebSockets don't sleep
    },
  });

  // Minimize to tray on close instead of exiting
  win.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault();
      win?.hide();

      // Notify the user so they know it is running in the tray
      if (tray && process.platform === 'win32' && !hasShownTrayBalloon) {
        hasShownTrayBalloon = true;
        tray.displayBalloon({
          title: 'Jarvis is running in background',
          content: 'Jarvis has minimized to your system tray. Click the tray icon or press Ctrl+Shift+J to reopen.',
        });
      }
      return false;
    }
  });

  win.webContents.setWindowOpenHandler(({ url }) => {
    // Force open in Chrome based on OS
    const isWindows = process.platform === 'win32';
    const isMac = process.platform === 'darwin';

    if (isWindows) {
      exec(`start chrome "${url}"`);
    } else if (isMac) {
      exec(`open -a "Google Chrome" "${url}"`);
    } else {
      exec(`google-chrome "${url}"`);
    }

    return { action: 'deny' };
  });

  if (VITE_DEV_SERVER_URL) {
    win.loadURL(VITE_DEV_SERVER_URL);
  } else {
    // Load the local bundled files instead of the remote Azure version
    win.loadFile(path.join(RENDERER_DIST, 'index.html'));
  }
}

app.on('before-quit', () => {
  isQuitting = true;
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin' && isQuitting) {
    app.quit();
    win = null;
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  } else if (win) {
    win.show();
    win.focus();
  }
});

// Setup IPC handlers
ipcMain.handle('run-command', async (_, command: string, cwd?: string) => {
  try {
    const { stdout, stderr } = await execAsync(command, { cwd });
    return { status: 'success', output: { stdout, stderr } };
  } catch (error: any) {
    return { status: 'error', error: error.message };
  }
});

ipcMain.handle('open-app', async (_, appName: string, url?: string) => {
  try {
    const isWindows = process.platform === 'win32';
    const isMac = process.platform === 'darwin';
    let command = '';

    if (isWindows) {
      command = `start "" "${appName}"`;
      if (url) command += ` "${url}"`;
    } else if (isMac) {
      command = url ? `open -a "${appName}" "${url}"` : `open -a "${appName}"`;
    } else {
      command = url ? `${appName} "${url}" &` : `${appName} &`;
    }

    await execAsync(command);
    return { status: 'success' };
  } catch (error: any) {
    return { status: 'error', error: error.message };
  }
});

ipcMain.handle('close-app', async (_, appName: string) => {
  try {
    const isWindows = process.platform === 'win32';
    const isMac = process.platform === 'darwin';
    let command = '';

    if (isWindows) {
      const processName = appName.toLowerCase().endsWith('.exe') ? appName : `${appName}.exe`;
      command = `taskkill /IM "${processName}" /F`;
    } else if (isMac) {
      command = `killall "${appName}"`;
    } else {
      command = `pkill -f "${appName}"`;
    }

    await execAsync(command);
    return { status: 'success' };
  } catch (error: any) {
    return { status: 'error', error: error.message };
  }
});

ipcMain.handle('open-external', async (_, url: string) => {
  try {
    await shell.openExternal(url);
    return { status: 'success' };
  } catch (error: any) {
    return { status: 'error', error: error.message };
  }
});

// Native OS Notifications
ipcMain.handle('show-notification', async (_, title: string, body: string) => {
  try {
    if (Notification.isSupported()) {
      const iconPath = path.join(process.env.VITE_PUBLIC || '', 'arc_reactor.png');
      const notif = new Notification({
        title: title || 'Jarvis Notification',
        body: body || '',
        icon: iconPath,
      });
      notif.show();
      notif.on('click', () => {
        if (win) {
          win.show();
          win.focus();
        }
      });
      return { status: 'success' };
    }
    return { status: 'error', error: 'OS notifications not supported' };
  } catch (error: any) {
    return { status: 'error', error: error.message };
  }
});

// Local Desktop Screen Capture
ipcMain.handle('capture-screen', async () => {
  try {
    const sources = await desktopCapturer.getSources({
      types: ['screen'],
      thumbnailSize: { width: 1920, height: 1080 },
    });
    if (sources.length === 0) {
      return { status: 'error', error: 'No display screen source detected' };
    }
    const primarySource = sources[0];
    const imageBase64 = primarySource.thumbnail.toDataURL(); // data:image/png;base64,...
    return { status: 'success', image_base64: imageBase64 };
  } catch (error: any) {
    return { status: 'error', error: error.message };
  }
});

app.whenReady().then(() => {
  // Configure auto-launch at system boot
  try {
    app.setLoginItemSettings({
      openAtLogin: true,
      openAsHidden: true,
      args: ['--hidden'],
    });
  } catch (err) {
    console.warn('Failed to set login item settings:', err);
  }

  createWindow();
  createTray();

  // If launched with --hidden argument, start minimized in system tray
  if (process.argv.includes('--hidden')) {
    win?.hide();
  }

  // Register global hotkey (CommandOrControl+Shift+J) to toggle Jarvis visibility
  try {
    globalShortcut.register('CommandOrControl+Shift+J', () => {
      if (win) {
        if (win.isVisible() && win.isFocused()) {
          win.hide();
        } else {
          win.show();
          win.focus();
        }
      }
    });
  } catch (err) {
    console.error('Failed to register global shortcut:', err);
  }
});
