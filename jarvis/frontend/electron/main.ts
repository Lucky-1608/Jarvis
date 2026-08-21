import { app, BrowserWindow, ipcMain } from 'electron';
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

let win: BrowserWindow | null;

function createWindow() {
  win = new BrowserWindow({
    width: 1200,
    height: 800,
    icon: path.join(process.env.VITE_PUBLIC || '', 'arc_reactor.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.mjs'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  if (VITE_DEV_SERVER_URL) {
    win.loadURL(VITE_DEV_SERVER_URL);
    // Open devtools by default in dev mode
    // win.webContents.openDevTools();
  } else {
    win.loadFile(path.join(RENDERER_DIST, 'index.html'));
  }
}

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
    win = null;
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
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

app.whenReady().then(createWindow);
