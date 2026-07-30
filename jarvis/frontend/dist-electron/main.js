import { app as n, BrowserWindow as t } from "electron";
import e from "node:path";
import { fileURLToPath as l } from "node:url";
const r = e.dirname(l(import.meta.url));
process.env.APP_ROOT = e.join(r, "..");
const i = process.env.VITE_DEV_SERVER_URL, R = e.join(process.env.APP_ROOT, "dist-electron"), s = e.join(process.env.APP_ROOT, "dist");
process.env.VITE_PUBLIC = i ? e.join(process.env.APP_ROOT, "public") : s;
let o;
function c() {
  o = new t({
    width: 1200,
    height: 800,
    icon: e.join(process.env.VITE_PUBLIC || "", "favicon.ico"),
    webPreferences: {
      preload: e.join(r, "preload.mjs"),
      nodeIntegration: !1,
      contextIsolation: !0
    }
  }), i ? o.loadURL(i) : o.loadFile(e.join(s, "index.html"));
}
n.on("window-all-closed", () => {
  process.platform !== "darwin" && (n.quit(), o = null);
});
n.on("activate", () => {
  t.getAllWindows().length === 0 && c();
});
n.whenReady().then(c);
export {
  R as MAIN_DIST,
  s as RENDERER_DIST,
  i as VITE_DEV_SERVER_URL
};
