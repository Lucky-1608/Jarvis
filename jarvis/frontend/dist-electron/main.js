import { BrowserWindow, Menu, Notification, Tray, app, desktopCapturer, globalShortcut, ipcMain, nativeImage, shell } from "electron";
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
var win = null;
var tray = null;
var isQuitting = false;
function createTray() {
	const iconPath = path.join(process.env.VITE_PUBLIC || "", "arc_reactor.png");
	let icon;
	try {
		icon = nativeImage.createFromPath(iconPath);
		if (icon.isEmpty()) icon = nativeImage.createEmpty();
	} catch {
		icon = nativeImage.createEmpty();
	}
	tray = new Tray(icon);
	tray.setToolTip("Jarvis Companion OS");
	const contextMenu = Menu.buildFromTemplate([
		{
			label: "Open Jarvis",
			click: () => {
				if (win) {
					win.show();
					win.focus();
				}
			}
		},
		{
			label: "Minimize to Tray",
			click: () => {
				win?.hide();
			}
		},
		{ type: "separator" },
		{
			label: "Shortcut: Ctrl+Shift+J / Cmd+Shift+J",
			enabled: false
		},
		{ type: "separator" },
		{
			label: "Quit Jarvis",
			click: () => {
				isQuitting = true;
				app.quit();
			}
		}
	]);
	tray.setContextMenu(contextMenu);
	tray.on("click", () => {
		if (win) {
			if (win.isVisible() && !win.isMinimized()) win.hide();
			else {
				win.show();
				win.focus();
			}
		}
	});
}
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
	win.on("close", (event) => {
		if (!isQuitting) {
			event.preventDefault();
			win?.hide();
			return false;
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
	else win.loadFile(path.join(RENDERER_DIST, "index.html"));
}
app.on("before-quit", () => {
	isQuitting = true;
});
app.on("will-quit", () => {
	globalShortcut.unregisterAll();
});
app.on("window-all-closed", () => {
	if (process.platform !== "darwin" && isQuitting) {
		app.quit();
		win = null;
	}
});
app.on("activate", () => {
	if (BrowserWindow.getAllWindows().length === 0) createWindow();
	else if (win) {
		win.show();
		win.focus();
	}
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
ipcMain.handle("show-notification", async (_, title, body) => {
	try {
		if (Notification.isSupported()) {
			const iconPath = path.join(process.env.VITE_PUBLIC || "", "arc_reactor.png");
			const notif = new Notification({
				title: title || "Jarvis Notification",
				body: body || "",
				icon: iconPath
			});
			notif.show();
			notif.on("click", () => {
				if (win) {
					win.show();
					win.focus();
				}
			});
			return { status: "success" };
		}
		return {
			status: "error",
			error: "OS notifications not supported"
		};
	} catch (error) {
		return {
			status: "error",
			error: error.message
		};
	}
});
ipcMain.handle("capture-screen", async () => {
	try {
		const sources = await desktopCapturer.getSources({
			types: ["screen"],
			thumbnailSize: {
				width: 1920,
				height: 1080
			}
		});
		if (sources.length === 0) return {
			status: "error",
			error: "No display screen source detected"
		};
		return {
			status: "success",
			image_base64: sources[0].thumbnail.toDataURL()
		};
	} catch (error) {
		return {
			status: "error",
			error: error.message
		};
	}
});
app.whenReady().then(() => {
	createWindow();
	createTray();
	try {
		globalShortcut.register("CommandOrControl+Shift+J", () => {
			if (win) {
				if (win.isVisible() && win.isFocused()) win.hide();
				else {
					win.show();
					win.focus();
				}
			}
		});
	} catch (err) {
		console.error("Failed to register global shortcut:", err);
	}
});
//#endregion
export { MAIN_DIST, RENDERER_DIST, VITE_DEV_SERVER_URL };
