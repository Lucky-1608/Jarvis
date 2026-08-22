import { BrowserWindow as e, app as t, ipcMain as n, shell as r } from "electron";
import i from "node:path";
import { fileURLToPath as a } from "node:url";
import { exec as o } from "node:child_process";
import s from "node:util";
//#region electron/main.ts
var c = s.promisify(o), l = i.dirname(a(import.meta.url));
process.env.APP_ROOT = i.join(l, "..");
var u = process.env.VITE_DEV_SERVER_URL, d = i.join(process.env.APP_ROOT, "dist-electron"), f = i.join(process.env.APP_ROOT, "dist");
process.env.VITE_PUBLIC = u ? i.join(process.env.APP_ROOT, "public") : f;
var p;
function m() {
	p = new e({
		width: 1200,
		height: 800,
		icon: i.join(process.env.VITE_PUBLIC || "", "arc_reactor.png"),
		webPreferences: {
			preload: i.join(l, "preload.mjs"),
			nodeIntegration: !1,
			contextIsolation: !0
		}
	}), u ? p.loadURL(u) : p.loadURL("https://jarvisos-gdhfgnc4gscqecav.centralindia-01.azurewebsites.net");
}
t.on("window-all-closed", () => {
	process.platform !== "darwin" && (t.quit(), p = null);
}), t.on("activate", () => {
	e.getAllWindows().length === 0 && m();
}), n.handle("run-command", async (e, t, n) => {
	try {
		let { stdout: e, stderr: r } = await c(t, { cwd: n });
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
}), n.handle("open-app", async (e, t, n) => {
	try {
		let e = process.platform === "win32", r = process.platform === "darwin", i = "";
		return e ? (i = `start "" "${t}"`, n && (i += ` "${n}"`)) : i = r ? n ? `open -a "${t}" "${n}"` : `open -a "${t}"` : n ? `${t} "${n}" &` : `${t} &`, await c(i), { status: "success" };
	} catch (e) {
		return {
			status: "error",
			error: e.message
		};
	}
}), n.handle("close-app", async (e, t) => {
	try {
		let e = process.platform === "win32", n = process.platform === "darwin", r = "";
		return r = e ? `taskkill /IM "${t.toLowerCase().endsWith(".exe") ? t : `${t}.exe`}" /F` : n ? `killall "${t}"` : `pkill -f "${t}"`, await c(r), { status: "success" };
	} catch (e) {
		return {
			status: "error",
			error: e.message
		};
	}
}), n.handle("open-external", async (e, t) => {
	try {
		return await r.openExternal(t), { status: "success" };
	} catch (e) {
		return {
			status: "error",
			error: e.message
		};
	}
}), t.whenReady().then(m);
//#endregion
export { d as MAIN_DIST, f as RENDERER_DIST, u as VITE_DEV_SERVER_URL };
