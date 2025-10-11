<<<<<<< HEAD
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  openFile: () => ipcRenderer.invoke("dialog:openFile")
});
=======
 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/client/electron/preload.js
index 0000000000000000000000000000000000000000..8134ef2fff61eeb9d8c0be5dda1b5c5bc7d4a0e9 100644
--- a//dev/null
+++ b/client/electron/preload.js
@@ -0,0 +1,5 @@
+const { contextBridge, ipcRenderer } = require("electron");
+
+contextBridge.exposeInMainWorld("electronAPI", {
+  openFile: () => ipcRenderer.invoke("dialog:openFile")
+});
 
EOF
)
>>>>>>> origin/main
