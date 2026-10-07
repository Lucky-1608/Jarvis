import { BrowserWindow as e, Menu as t, Notification as n, Tray as r, app as i, desktopCapturer as a, globalShortcut as o, ipcMain as s, nativeImage as c, shell as l } from "electron";
import u from "node:path";
import { fileURLToPath as d } from "node:url";
import { exec as f } from "node:child_process";
import p from "node:util";
//#region electron/main.ts
var m = p.promisify(f), h = u.dirname(d(import.meta.url));
process.env.APP_ROOT = u.join(h, "..");
var g = process.env.VITE_DEV_SERVER_URL, _ = u.join(process.env.APP_ROOT, "dist-electron"), v = u.join(process.env.APP_ROOT, "dist");
process.env.VITE_PUBLIC = g ? u.join(process.env.APP_ROOT, "public") : v;
var y = null, b = null, x = !1;
function S() {
	let e = u.join(process.env.VITE_PUBLIC || "", "arc_reactor.png"), n;
	try {
		n = c.createFromPath(e), n.isEmpty() && (n = c.createEmpty());
	} catch {
		n = c.createEmpty();
	}
	b = new r(n), b.setToolTip("Jarvis Companion OS");
	let a = t.buildFromTemplate([
		{
			label: "Open Jarvis",
			click: () => {
				y && (y.show(), y.focus());
			}
		},
		{
			label: "Minimize to Tray",
			click: () => {
				y?.hide();
			}
		},
		{ type: "separator" },
		{
			label: "Shortcut: Ctrl+Shift+J / Cmd+Shift+J",
			enabled: !1
		},
		{ type: "separator" },
		{
			label: "Quit Jarvis",
			click: () => {
				x = !0, i.quit();
			}
		}
	]);
	b.setContextMenu(a), b.on("click", () => {
		y && (y.isVisible() && !y.isMinimized() ? y.hide() : (y.show(), y.focus()));
	});
}
function C() {
	y = new e({
		width: 1200,
		height: 800,
		icon: u.join(process.env.VITE_PUBLIC || "", "arc_reactor.png"),
		webPreferences: {
			preload: u.join(h, "preload.mjs"),
			nodeIntegration: !1,
			contextIsolation: !0
		}
	}), y.on("close", (e) => {
		if (!x) return e.preventDefault(), y?.hide(), !1;
	}), y.webContents.setWindowOpenHandler(({ url: e }) => {
		let t = process.platform === "win32", n = process.platform === "darwin";
		return f(t ? `start chrome "${e}"` : n ? `open -a "Google Chrome" "${e}"` : `google-chrome "${e}"`), { action: "deny" };
	}), g ? y.loadURL(g) : y.loadFile(u.join(v, "index.html"));
}
i.on("before-quit", () => {
	x = !0;
}), i.on("will-quit", () => {
	o.unregisterAll();
}), i.on("window-all-closed", () => {
	process.platform !== "darwin" && x && (i.quit(), y = null);
}), i.on("activate", () => {
	e.getAllWindows().length === 0 ? C() : y && (y.show(), y.focus());
}), s.handle("run-command", async (e, t, n) => {
	try {
		let { stdout: e, stderr: r } = await m(t, { cwd: n });
		return {
			status: "success",
			output: {
				stdout: e,
				stderr: r
			}
		};
	} catch (e) {
		return {
			status: "error",
			error: e.message
		};
	}
}), s.handle("open-app", async (e, t, n) => {
	try {
		let e = process.platform === "win32", r = process.platform === "darwin", i = "";
		return e ? (i = `start "" "${t}"`, n && (i += ` "${n}"`)) : i = r ? n ? `open -a "${t}" "${n}"` : `open -a "${t}"` : n ? `${t} "${n}" &` : `${t} &`, await m(i), { status: "success" };
	} catch (e) {
		return {
			status: "error",
			error: e.message
		};
	}
}), s.handle("close-app", async (e, t) => {
	try {
		let e = process.platform === "win32", n = process.platform === "darwin", r = "";
		return r = e ? `taskkill /IM "${t.toLowerCase().endsWith(".exe") ? t : `${t}.exe`}" /F` : n ? `killall "${t}"` : `pkill -f "${t}"`, await m(r), { status: "success" };
	} catch (e) {
		return {
			status: "error",
			error: e.message
		};
	}
}), s.handle("open-external", async (e, t) => {
	try {
		return await l.openExternal(t), { status: "success" };
	} catch (e) {
		return {
			status: "error",
			error: e.message
		};
	}
}), s.handle("show-notification", async (e, t, r) => {
	try {
		if (n.isSupported()) {
			let e = u.join(process.env.VITE_PUBLIC || "", "arc_reactor.png"), i = new n({
				title: t || "Jarvis Notification",
				body: r || "",
				icon: e
			});
			return i.show(), i.on("click", () => {
				y && (y.show(), y.focus());
			}), { status: "success" };
		}
		return {
			status: "error",
			error: "OS notifications not supported"
		};
	} catch (e) {
		return {
			status: "error",
			error: e.message
		};
	}
}), s.handle("capture-screen", async () => {
	try {
		let e = await a.getSources({
			types: ["screen"],
			thumbnailSize: {
				width: 1920,
				height: 1080
			}
		});
		return e.length === 0 ? {
			status: "error",
			error: "No display screen source detected"
		} : {
			status: "success",
			image_base64: e[0].thumbnail.toDataURL()
		};
	} catch (e) {
		return {
			status: "error",
			error: e.message
		};
	}
}), i.whenReady().then(() => {
	C(), S();
	try {
		o.register("CommandOrControl+Shift+J", () => {
			y && (y.isVisible() && y.isFocused() ? y.hide() : (y.show(), y.focus()));
		});
	} catch (e) {
		console.error("Failed to register global shortcut:", e);
	}
});
//#endregion
export { _ as MAIN_DIST, v as RENDERER_DIST, g as VITE_DEV_SERVER_URL };
