 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/client/electron/main.js
index 0000000000000000000000000000000000000000..842718bd50911395e8e4f3ef34c452ba1a6be64c 100644
--- a//dev/null
+++ b/client/electron/main.js
@@ -0,0 +1,52 @@
+const { app, BrowserWindow, dialog, ipcMain } = require("electron");
+const path = require("node:path");
+const fs = require("node:fs");
+
+const isDev = !app.isPackaged;
+
+const createWindow = async () => {
+  const mainWindow = new BrowserWindow({
+    width: 1280,
+    height: 800,
+    webPreferences: {
+      preload: path.join(__dirname, "preload.js"),
+      nodeIntegration: false,
+      contextIsolation: true
+    }
+  });
+
+  const devServerURL = process.env.VITE_DEV_SERVER_URL;
+  if (isDev && devServerURL) {
+    await mainWindow.loadURL(devServerURL);
+    mainWindow.webContents.openDevTools();
+  } else {
+    await mainWindow.loadFile(path.join(__dirname, "../renderer/index.html"));
+  }
+};
+
+app.whenReady().then(createWindow);
+
+app.on("window-all-closed", () => {
+  if (process.platform !== "darwin") {
+    app.quit();
+  }
+});
+
+app.on("activate", async () => {
+  if (BrowserWindow.getAllWindows().length === 0) {
+    await createWindow();
+  }
+});
+
+ipcMain.handle("dialog:openFile", async () => {
+  const { canceled, filePaths } = await dialog.showOpenDialog({
+    properties: ["openFile"],
+    filters: [{ name: "Images", extensions: ["png", "jpg", "jpeg", "tiff"] }]
+  });
+  if (canceled || filePaths.length === 0) {
+    return null;
+  }
+  const filePath = filePaths[0];
+  const buffer = fs.readFileSync(filePath);
+  return { filePath, buffer: buffer.toString("base64") };
+});
 
EOF
)
