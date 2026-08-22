import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('electronAPI', {
  runCommand: (command: string, cwd?: string) => ipcRenderer.invoke('run-command', command, cwd),
  openApp: (appName: string, url?: string) => ipcRenderer.invoke('open-app', appName, url),
  closeApp: (appName: string) => ipcRenderer.invoke('close-app', appName),
  openExternal: (url: string) => ipcRenderer.invoke('open-external', url)
});
