const {
  app,
  BrowserWindow,
  ipcMain,
  dialog,
  Tray,
  Menu,
  nativeImage,
} = require('electron');
const path = require('path');
const { exec } = require('child_process');
const util = require('util');

const execAsync = util.promisify(exec);

let mainWindow = null;
let tray = null;
let store = null;

// Lazy-import electron-store (ESM/CJS interop)
async function getStore() {
  if (store) return store;
  const ElectronStore = (await import('electron-store')).default;
  store = new ElectronStore({ defaults: { db_path: '' } });
  return store;
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    minWidth: 600,
    minHeight: 400,
    icon: path.join(__dirname, 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, 'index.html'));

  // Minimize to tray instead of closing
  mainWindow.on('close', (event) => {
    if (!app.isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function createTray() {
  // Create a 24x24 icon programmatically (solid colour tile)
  const icon = nativeImage.createEmpty();
  const size = 24;
  // Fallback: create a small PNG buffer
  const canvas = Buffer.alloc(size * size * 4);
  for (let i = 0; i < size * size; i++) {
    const offset = i * 4;
    canvas[offset] = 59;     // R  #3b
    canvas[offset + 1] = 130; // G #82
    canvas[offset + 2] = 246; // B #f6
    canvas[offset + 3] = 255; // A
  }
  const trayIcon = nativeImage.createFromBuffer(canvas, {
    width: size,
    height: size,
  });
  tray = new Tray(trayIcon);
  tray.setToolTip('Brain4me Desktop');

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Open',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        } else {
          createWindow();
        }
      },
    },
    {
      label: 'Ingest Files',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
          mainWindow.webContents.send('tray:ingest');
        } else {
          createWindow();
        }
      },
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        app.isQuitting = true;
        app.quit();
      },
    },
  ]);

  tray.setContextMenu(contextMenu);
  tray.on('double-click', () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    } else {
      createWindow();
    }
  });
}

// ── IPC Handlers ────────────────────────────────────────────────────────────

ipcMain.handle('dialog:openFiles', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile', 'multiSelections'],
    filters: [
      { name: 'Supported Documents', extensions: ['pdf', 'docx', 'doc', 'txt', 'md', 'markdown'] },
      { name: 'PDF Files', extensions: ['pdf'] },
      { name: 'Word Documents', extensions: ['docx', 'doc'] },
      { name: 'Text Files', extensions: ['txt'] },
      { name: 'Markdown', extensions: ['md', 'markdown'] },
      { name: 'All Files', extensions: ['*'] },
    ],
  });

  if (result.canceled) return [];
  return result.filePaths;
});

ipcMain.handle('config:get', async () => {
  const s = await getStore();
  return { db_path: s.get('db_path', '') };
});

ipcMain.handle('config:set', async (_event, key, value) => {
  const s = await getStore();
  s.set(key, value);
  return { ok: true };
});

ipcMain.handle('ingest:file', async (_event, filePath) => {
  const s = await getStore();
  const dbPath = s.get('db_path', '');

  if (!dbPath) {
    return { ok: false, error: 'db_path not configured. Set it in the Config section.' };
  }

  try {
    const cmd = `brain4me ingest --db "${dbPath}" "${filePath}"`;
    const { stdout, stderr } = await execAsync(cmd, { timeout: 120000 });

    // Try to parse the JSON output from the CLI
    let result;
    try {
      result = JSON.parse(stdout.trim());
    } catch {
      result = { raw: stdout.trim() };
    }

    return { ok: true, filePath, result, stderr: stderr.trim() };
  } catch (err) {
    let message = err.message || String(err);

    // Check if brain4me is installed
    if (message.includes('ENOENT') || message.includes('command not found')) {
      return {
        ok: false,
        filePath,
        error:
          'brain4me CLI not found in PATH. Make sure it is installed:\n\n  pip install -e .\n\nor activate the correct Python virtual environment.',
      };
    }

    return { ok: false, filePath, error: message };
  }
});

ipcMain.handle('ingest:batch', async (_event, filePaths) => {
  const results = [];

  for (let i = 0; i < filePaths.length; i++) {
    const filePath = filePaths[i];
    const progress = { current: i + 1, total: filePaths.length, filePath };

    // Send progress to renderer
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('ingest:progress', {
        ...progress,
        status: 'processing',
      });
    }

    // Invoke the single-file handler
    const s = await getStore();
    const dbPath = s.get('db_path', '');

    if (!dbPath) {
      const errResult = { ok: false, filePath, error: 'db_path not configured.' };
      results.push(errResult);
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('ingest:progress', {
          ...progress,
          status: 'error',
          error: 'db_path not configured.',
        });
      }
      continue;
    }

    try {
      const cmd = `brain4me ingest --db "${dbPath}" "${filePath}"`;
      const { stdout, stderr } = await execAsync(cmd, { timeout: 120000 });

      let result;
      try {
        result = JSON.parse(stdout.trim());
      } catch {
        result = { raw: stdout.trim() };
      }

      const item = { ok: true, filePath, result, stderr: stderr.trim() };
      results.push(item);

      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('ingest:progress', {
          ...progress,
          status: 'done',
          result: item,
        });
      }
    } catch (err) {
      let message = err.message || String(err);
      if (message.includes('ENOENT') || message.includes('command not found')) {
        message =
          'brain4me CLI not found in PATH. Make sure it is installed:\n\n  pip install -e .';
      }

      const item = { ok: false, filePath, error: message };
      results.push(item);

      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('ingest:progress', {
          ...progress,
          status: 'error',
          error: message,
        });
      }
    }
  }

  // Final summary
  const succeeded = results.filter((r) => r.ok).length;
  const failed = results.filter((r) => !r.ok).length;
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('ingest:progress', {
      current: filePaths.length,
      total: filePaths.length,
      status: 'complete',
      succeeded,
      failed,
    });
  }

  return results;
});

// ── App Lifecycle ──────────────────────────────────────────────────────────

app.whenReady().then(async () => {
  createWindow();
  createTray();

  // Provide a summary endpoint the renderer can fetch on load
  ipcMain.handle('summary:get', async () => {
    const s = await getStore();
    const dbPath = s.get('db_path', '');

    if (!dbPath) {
      return { ok: false, error: 'db_path not configured.' };
    }

    try {
      const { stdout } = await execAsync(`brain4me summary --db "${dbPath}" --json`, {
        timeout: 15000,
      });
      return { ok: true, data: JSON.parse(stdout.trim()) };
    } catch (err) {
      return { ok: false, error: err.message };
    }
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    } else if (mainWindow) {
      mainWindow.show();
    }
  });
});

app.on('window-all-closed', () => {
  // On Linux/macOS we keep the app alive in the tray
  // Only quit if explicitly requested via tray menu
  if (process.platform === 'darwin') {
    app.dock.hide();
  }
});

app.on('before-quit', () => {
  app.isQuitting = true;
});
