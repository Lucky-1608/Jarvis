import { BrowserWindow as e, app as t, ipcMain as n } from "electron";
import r from "node:path";
import { fileURLToPath as i } from "node:url";
import { exec as a } from "node:child_process";
import o from "node:util";
//#region electron/main.ts
var s = o.promisify(a), c = r.dirname(i(import.meta.url));
process.env.APP_ROOT = r.join(c, "..");
var l = process.env.VITE_DEV_SERVER_URL, u = r.join(process.env.APP_ROOT, "dist-electron"), d = r.join(process.env.APP_ROOT, "dist");
process.env.VITE_PUBLIC = l ? r.join(process.env.APP_ROOT, "public") : d;
var f;
function p() {
	f = new e({
		width: 1200,
		height: 800,
		icon: r.join(process.env.VITE_PUBLIC || "", "arc_reactor.png"),
		webPreferences: {
			preload: r.join(c, "preload.mjs"),
			nodeIntegration: !1,
			contextIsolation: !0
		}
	}), l ? f.loadURL(l) : f.loadURL("https://jarvisos-gdhfgnc4gscqecav.centralindia-01.azurewebsites.net");
}
t.on("window-all-closed", () => {
	process.platform !== "darwin" && (t.quit(), f = null);
}), t.on("activate", () => {
	e.getAllWindows().length === 0 && p();
}), n.handle("run-command", async (e, t, n) => {
	try {
		let { stdout: e, stderr: r } = await s(t, { cwd: n });
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
		return e ? (i = `start "" "${t}"`, n && (i += ` "${n}"`)) : i = r ? n ? `open -a "${t}" "${n}"` : `open -a "${t}"` : n ? `${t} "${n}" &` : `${t} &`, await s(i), { status: "success" };
	} catch (e) {
		return {
			status: "error",
			error: e.message
		};
	}
}), n.handle("close-app", async (e, t) => {
	try {
		let e = process.platform === "win32", n = process.platform === "darwin", r = "";
		return r = e ? `taskkill /IM "${t.toLowerCase().endsWith(".exe") ? t : `${t}.exe`}" /F` : n ? `killall "${t}"` : `pkill -f "${t}"`, await s(r), { status: "success" };
	} catch (e) {
		return {
			status: "error",
			error: e.message
		};
	}
}), t.whenReady().then(p);
//#endregion
export { u as MAIN_DIST, d as RENDERER_DIST, l as VITE_DEV_SERVER_URL };
