 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/client/.eslintrc.cjs
index 0000000000000000000000000000000000000000..97dd3a7617c4c367aca9841903294f72b9593414 100644
--- a//dev/null
+++ b/client/.eslintrc.cjs
@@ -0,0 +1,19 @@
+module.exports = {
+  root: true,
+  env: {
+    browser: true,
+    es2021: true
+  },
+  extends: ["eslint:recommended", "plugin:react-hooks/recommended", "prettier"],
+  parserOptions: {
+    ecmaVersion: "latest",
+    sourceType: "module"
+  },
+  rules: {},
+  ignorePatterns: ["dist", "electron/*.js"],
+  settings: {
+    react: {
+      version: "detect"
+    }
+  }
+};
 
EOF
)
