import { BrowserWindow, app, ipcMain, shell } from "electron";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { exec } from "node:child_process";
import util from "node:util";
//#region electron/main.ts
var execAsync = util.promisify(exec);
var __dirname = path.dirname(fileURLToPath(import.meta.url));
process.env.APP_ROOT = path.join(__dirname, "..");
var VITE_DEV_SERVER_URL = process.env["VITE_DEV_SERVER_URL"];
var MAIN_DIST = path.join(process.env.APP_ROOT, "dist-electron");
var RENDERER_DIST = path.join(process.env.APP_ROOT, "dist");
process.env.VITE_PUBLIC = VITE_DEV_SERVER_URL ? path.join(process.env.APP_ROOT, "public") : RENDERER_DIST;
var win;
function createWindow() {
	win = new BrowserWindow({
		width: 1200,
		height: 800,
		icon: path.join(process.env.VITE_PUBLIC || "", "arc_reactor.png"),
		webPreferences: {
			preload: path.join(__dirname, "preload.mjs"),
			nodeIntegration: false,
			contextIsolation: true
		}
	});
	win.webContents.setWindowOpenHandler(({ url }) => {
		const isWindows = process.platform === "win32";
		const isMac = process.platform === "darwin";
		if (isWindows) exec(`start chrome "${url}"`);
		else if (isMac) exec(`open -a "Google Chrome" "${url}"`);
		else exec(`google-chrome "${url}"`);
		return { action: "deny" };
	});
	if (VITE_DEV_SERVER_URL) win.loadURL(VITE_DEV_SERVER_URL);
	else win.loadURL("https://jarvisos-gdhfgnc4gscqecav.centralindia-01.azurewebsites.net");
}
app.on("window-all-closed", () => {
	if (process.platform !== "darwin") {
		app.quit();
		win = null;
	}
});
app.on("activate", () => {
	if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
ipcMain.handle("run-command", async (_, command, cwd) => {
	try {
		const { stdout, stderr } = await execAsync(command, { cwd });
		return {
			status: "success",
			output: {
				stdout,
				stderr
			}
		};
	} catch (error) {
		return {
			status: "error",
			error: error.message
		};
	}
});
ipcMain.handle("open-app", async (_, appName, url) => {
	try {
		const isWindows = process.platform === "win32";
		const isMac = process.platform === "darwin";
		let command = "";
		if (isWindows) {
			command = `start "" "${appName}"`;
			if (url) command += ` "${url}"`;
		} else if (isMac) command = url ? `open -a "${appName}" "${url}"` : `open -a "${appName}"`;
		else command = url ? `${appName} "${url}" &` : `${appName} &`;
		await execAsync(command);
		return { status: "success" };
	} catch (error) {
		return {
			status: "error",
			error: error.message
		};
	}
});
ipcMain.handle("close-app", async (_, appName) => {
	try {
		const isWindows = process.platform === "win32";
		const isMac = process.platform === "darwin";
		let command = "";
		if (isWindows) command = `taskkill /IM "${appName.toLowerCase().endsWith(".exe") ? appName : `${appName}.exe`}" /F`;
		else if (isMac) command = `killall "${appName}"`;
		else command = `pkill -f "${appName}"`;
		await execAsync(command);
		return { status: "success" };
	} catch (error) {
		return {
			status: "error",
			error: error.message
		};
	}
});
ipcMain.handle("open-external", async (_, url) => {
	try {
		await shell.openExternal(url);
		return { status: "success" };
	} catch (error) {
		return {
			status: "error",
			error: error.message
		};
	}
});
app.whenReady().then(createWindow);
//#endregion
export { MAIN_DIST, RENDERER_DIST, VITE_DEV_SERVER_URL };
