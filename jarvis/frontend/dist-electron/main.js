import { BrowserWindow as e, Menu as t, Notification as n, Tray as r, app as i, desktopCapturer as a, globalShortcut as o, ipcMain as s, nativeImage as c, shell as l } from "electron";
import u from "node:fs";
import d from "node:path";
import { fileURLToPath as f } from "node:url";
import { exec as p } from "node:child_process";
import m from "node:util";
//#region electron/main.ts
var h = m.promisify(p), g = d.dirname(f(import.meta.url));
process.env.APP_ROOT = d.join(g, "..");
var _ = process.env.VITE_DEV_SERVER_URL, v = d.join(process.env.APP_ROOT, "dist-electron"), y = d.join(process.env.APP_ROOT, "dist");
process.env.VITE_PUBLIC = _ ? d.join(process.env.APP_ROOT, "public") : y;
var b = null, x = null, S = !1, C = !1;
function w() {
	let e = [
		d.join(process.env.VITE_PUBLIC || "", "arc_reactor.png"),
		d.join(g, "../public/arc_reactor.png"),
		d.join(g, "../dist/arc_reactor.png"),
		d.join(process.cwd(), "public/arc_reactor.png"),
		d.join(process.cwd(), "dist/arc_reactor.png"),
		d.join(process.cwd(), "jarvis/frontend/public/arc_reactor.png"),
		d.join(process.cwd(), "jarvis/frontend/dist/arc_reactor.png"),
		d.join(i.getAppPath(), "public/arc_reactor.png"),
		d.join(i.getAppPath(), "dist/arc_reactor.png")
	];
	for (let t of e) try {
		if (u.existsSync(t)) return t;
	} catch {}
	return null;
}
function T() {
	let e = w();
	if (e) try {
		let t = c.createFromPath(e);
		if (!t.isEmpty()) return t;
	} catch (t) {
		console.warn("Failed to load icon from path:", e, t);
	}
	return c.createFromDataURL(`data:image/svg+xml;base64,${Buffer.from("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"64\" height=\"64\" viewBox=\"0 0 64 64\">\n    <circle cx=\"32\" cy=\"32\" r=\"28\" fill=\"#030712\" stroke=\"#00d8ff\" stroke-width=\"4\"/>\n    <circle cx=\"32\" cy=\"32\" r=\"16\" fill=\"#00d8ff\" fill-opacity=\"0.4\" stroke=\"#38bdf8\" stroke-width=\"3\"/>\n    <circle cx=\"32\" cy=\"32\" r=\"6\" fill=\"#ffffff\"/>\n  </svg>").toString("base64")}`);
}
function E() {
	return T().resize({
		width: 16,
		height: 16
	});
}
function D() {
	if (!x) try {
		let e = E();
		x = new r(e), x.setToolTip("Jarvis Companion OS");
		let n = t.buildFromTemplate([
			{
				label: "Open Jarvis",
				click: () => {
					b && (b.show(), b.focus());
				}
			},
			{
				label: "Minimize to Tray",
				click: () => {
					b?.hide();
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
					S = !0, i.quit();
				}
			}
		]);
		x.setContextMenu(n), x.on("click", () => {
			b && (b.isVisible() && !b.isMinimized() ? b.hide() : (b.show(), b.focus()));
		}), x.on("double-click", () => {
			b && (b.show(), b.focus());
		});
	} catch (e) {
		console.error("Failed to initialize system tray:", e);
	}
}
function O() {
	let t = T();
	b = new e({
		width: 1200,
		height: 800,
		icon: t,
		webPreferences: {
			preload: d.join(g, "preload.mjs"),
			nodeIntegration: !1,
			contextIsolation: !0,
			backgroundThrottling: !1
		}
	}), b.on("close", (e) => {
		if (!S) return e.preventDefault(), b?.hide(), x && process.platform === "win32" && !C && (C = !0, x.displayBalloon({
			title: "Jarvis is running in background",
			content: "Jarvis has minimized to your system tray. Click the tray icon or press Ctrl+Shift+J to reopen."
		})), !1;
	}), b.webContents.setWindowOpenHandler(({ url: e }) => {
		let t = process.platform === "win32", n = process.platform === "darwin";
		return p(t ? `start chrome "${e}"` : n ? `open -a "Google Chrome" "${e}"` : `google-chrome "${e}"`), { action: "deny" };
	}), _ ? b.loadURL(_) : b.loadFile(d.join(y, "index.html"));
}
i.on("before-quit", () => {
	S = !0;
}), i.on("will-quit", () => {
	o.unregisterAll();
}), i.on("window-all-closed", () => {
	process.platform !== "darwin" && S && (i.quit(), b = null);
}), i.on("activate", () => {
	e.getAllWindows().length === 0 ? O() : b && (b.show(), b.focus());
}), s.handle("run-command", async (e, t, n) => {
	try {
		let { stdout: e, stderr: r } = await h(t, { cwd: n });
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
		return e ? (i = `start "" "${t}"`, n && (i += ` "${n}"`)) : i = r ? n ? `open -a "${t}" "${n}"` : `open -a "${t}"` : n ? `${t} "${n}" &` : `${t} &`, await h(i), { status: "success" };
	} catch (e) {
		return {
			status: "error",
			error: e.message
		};
	}
}), s.handle("close-app", async (e, t) => {
	try {
		let e = process.platform === "win32", n = process.platform === "darwin", r = "";
		return r = e ? `taskkill /IM "${t.toLowerCase().endsWith(".exe") ? t : `${t}.exe`}" /F` : n ? `killall "${t}"` : `pkill -f "${t}"`, await h(r), { status: "success" };
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
			let e = d.join(process.env.VITE_PUBLIC || "", "arc_reactor.png"), i = new n({
				title: t || "Jarvis Notification",
				body: r || "",
				icon: e
			});
			return i.show(), i.on("click", () => {
				b && (b.show(), b.focus());
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
	try {
		i.setLoginItemSettings({
			openAtLogin: !0,
			openAsHidden: !0,
			args: ["--hidden"]
		});
	} catch (e) {
		console.warn("Failed to set login item settings:", e);
	}
	O(), D(), process.argv.includes("--hidden") && b?.hide();
	try {
		o.register("CommandOrControl+Shift+J", () => {
			b && (b.isVisible() && b.isFocused() ? b.hide() : (b.show(), b.focus()));
		});
	} catch (e) {
		console.error("Failed to register global shortcut:", e);
	}
});
//#endregion
export { v as MAIN_DIST, y as RENDERER_DIST, _ as VITE_DEV_SERVER_URL };
