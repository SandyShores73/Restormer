<<<<<<< HEAD
import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import "./styles.css";

const client = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
);
=======
 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/client/src/main.tsx
index 0000000000000000000000000000000000000000..cfb0b9821ffc44559c0afb709fba634d2a7af867 100644
--- a//dev/null
+++ b/client/src/main.tsx
@@ -0,0 +1,15 @@
+import React from "react";
+import ReactDOM from "react-dom/client";
+import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
+import App from "./App";
+import "./styles.css";
+
+const client = new QueryClient();
+
+ReactDOM.createRoot(document.getElementById("root")!).render(
+  <React.StrictMode>
+    <QueryClientProvider client={client}>
+      <App />
+    </QueryClientProvider>
+  </React.StrictMode>
+);
 
EOF
)
>>>>>>> origin/main
