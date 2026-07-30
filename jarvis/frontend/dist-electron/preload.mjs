"use strict";
const electron = require("electron");
electron.contextBridge.exposeInMainWorld("electronAPI", {
  // Example:
  // sendMessage: (msg: string) => ipcRenderer.send('message', msg)
});
