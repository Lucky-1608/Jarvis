import { contextBridge } from 'electron';

// Expose safe APIs to the renderer process
contextBridge.exposeInMainWorld('electronAPI', {
  // Example:
  // sendMessage: (msg: string) => ipcRenderer.send('message', msg)
});
