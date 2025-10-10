 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/client/src/global.d.ts
index 0000000000000000000000000000000000000000..16e03b0ee58c7b0718581cb7b25216ce677dd2d5 100644
--- a//dev/null
+++ b/client/src/global.d.ts
@@ -0,0 +1,9 @@
+export {}; // ensure treated as module
+
+declare global {
+  interface Window {
+    electronAPI: {
+      openFile: () => Promise<{ filePath: string; buffer: string } | null>;
+    };
+  }
+}
 
EOF
)
