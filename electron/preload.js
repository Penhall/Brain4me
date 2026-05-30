const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('brain4me', {
  openFiles: () => ipcRenderer.invoke('dialog:openFiles'),
  getConfig: () => ipcRenderer.invoke('config:get'),
  setConfig: (key, value) => ipcRenderer.invoke('config:set', key, value),
  ingestFile: (filePath) => ipcRenderer.invoke('ingest:file', filePath),
  ingestBatch: (filePaths) => ipcRenderer.invoke('ingest:batch', filePaths),
  getSummary: () => ipcRenderer.invoke('summary:get'),

  onIngestProgress: (callback) =>
    ipcRenderer.on('ingest:progress', (_event, data) => callback(data)),
  onTrayIngest: (callback) =>
    ipcRenderer.on('tray:ingest', () => callback()),
});
