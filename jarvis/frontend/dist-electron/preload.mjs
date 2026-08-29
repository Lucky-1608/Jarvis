let electron = require("electron");
//#region electron/preload.ts
electron.contextBridge.exposeInMainWorld("electronAPI", {
	runCommand: (command, cwd) => electron.ipcRenderer.invoke("run-command", command, cwd),
	openApp: (appName, url) => electron.ipcRenderer.invoke("open-app", appName, url),
	closeApp: (appName) => electron.ipcRenderer.invoke("close-app", appName),
	openExternal: (url) => electron.ipcRenderer.invoke("open-external", url)
});
//#endregion
