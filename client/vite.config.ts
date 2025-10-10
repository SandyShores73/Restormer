 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/client/vite.config.ts
index 0000000000000000000000000000000000000000..547a34bd1dbc50f9e9bdf1eb3abc207e1804923a 100644
--- a//dev/null
+++ b/client/vite.config.ts
@@ -0,0 +1,11 @@
+import { defineConfig } from "vite";
+import react from "@vitejs/plugin-react";
+
+export default defineConfig({
+  plugins: [react()],
+  base: "./",
+  build: {
+    outDir: "dist/renderer",
+    emptyOutDir: true
+  }
+});
 
EOF
)
