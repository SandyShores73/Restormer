const { app, BrowserWindow, dialog, ipcMain } = require("electron");
const path = require("node:path");
const fs = require("node:fs");

const isDev = !app.isPackaged;

const createWindow = async () => {
  const mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1024,
    minHeight: 640,
    show: false,
    backgroundColor: "#05060a",
    titleBarStyle: "hiddenInset",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  const showFallback = setTimeout(() => {
    if (!mainWindow.isDestroyed() && !mainWindow.isVisible()) {
      mainWindow.show();
    }
  }, 3000);

  const devServerURL = process.env.VITE_DEV_SERVER_URL;
  if (isDev && devServerURL) {
    await mainWindow.loadURL(devServerURL);
  } else {
    const distDir = path.join(__dirname, "../dist");
    const rendererPath = path.join(distDir, "renderer/index.html");
    const fallbackPath = path.join(distDir, "index.html");
    const target = fs.existsSync(rendererPath) ? rendererPath : fallbackPath;
    await mainWindow.loadFile(target);
  }

  mainWindow.once("ready-to-show", () => {
    clearTimeout(showFallback);
    if (!mainWindow.isDestroyed()) {
      mainWindow.show();
      mainWindow.setTitle("Luma Studio");
      mainWindow.focus();
    }
  });
};

app.whenReady().then(() => {
  app.setName("Luma Studio");
  createWindow();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", async () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    await createWindow();
  }
});

ipcMain.handle("dialog:openFiles", async () => {
  const { canceled, filePaths } = await dialog.showOpenDialog({
    properties: ["openFile", "multiSelections"],
    filters: [{ name: "Images", extensions: ["png", "jpg", "jpeg", "tiff", "tif"] }]
  });
  if (canceled || filePaths.length === 0) {
    return [];
  }
  const selected = filePaths.slice(0, 25);
  return selected.map((filePath) => {
    const buffer = fs.readFileSync(filePath);
    return { filePath, buffer: buffer.toString("base64") };
  });
});
