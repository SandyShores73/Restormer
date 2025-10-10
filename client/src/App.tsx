 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/client/src/App.tsx
index 0000000000000000000000000000000000000000..dce29a0feb3915e109fea078e235b24e651cd93f 100644
--- a//dev/null
+++ b/client/src/App.tsx
@@ -0,0 +1,130 @@
+import React, { useState } from "react";
+import { useMutation, useQuery } from "@tanstack/react-query";
+import { downloadProcessedImage, fetchJobs, loginWithPassword, loginWithGoogle, uploadJob } from "./api";
+
+const App: React.FC = () => {
+  const [token, setToken] = useState<string | null>(null);
+  const [email, setEmail] = useState("");
+  const [password, setPassword] = useState("");
+  const [googleToken, setGoogleToken] = useState("");
+
+  const jobsQuery = useQuery({
+    queryKey: ["jobs", token],
+    queryFn: () => fetchJobs(token!),
+    enabled: Boolean(token)
+  });
+
+  const loginMutation = useMutation({
+    mutationFn: () => loginWithPassword(email, password),
+    onSuccess: (response) => setToken(response.access_token)
+  });
+
+  const googleMutation = useMutation({
+    mutationFn: () => loginWithGoogle(googleToken),
+    onSuccess: (response) => setToken(response.access_token)
+  });
+
+  const uploadMutation = useMutation({
+    mutationFn: uploadJob,
+    onSuccess: () => jobsQuery.refetch()
+  });
+
+  const handleSelectFile = async () => {
+    const file = await window.electronAPI.openFile();
+    if (!file || !token) {
+      return;
+    }
+    const byteCharacters = atob(file.buffer);
+    const byteNumbers = new Array(byteCharacters.length)
+      .fill(0)
+      .map((_, idx) => byteCharacters.charCodeAt(idx));
+    const byteArray = new Uint8Array(byteNumbers);
+    const blob = new Blob([byteArray.buffer]);
+    const filename = file.filePath.split(/\\/).pop() ?? "upload.png";
+    const formData = new FormData();
+    formData.append("file", blob, filename);
+    await uploadMutation.mutateAsync({ token, data: formData });
+  };
+
+  const handleDownload = async (jobId: number) => {
+    if (!token) return;
+    await downloadProcessedImage(token, jobId);
+  };
+
+  return (
+    <div className="container">
+      <header>
+        <h1>Restormer Remote</h1>
+        <p>GPU accelerated denoise, detail refinement, and focus restoration.</p>
+      </header>
+
+      <section className="login-section">
+        <div className="form-group">
+          <label>Email</label>
+          <input value={email} onChange={(e) => setEmail(e.target.value)} />
+        </div>
+        <div className="form-group">
+          <label>Password</label>
+          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
+        </div>
+        <button onClick={() => loginMutation.mutate()} disabled={loginMutation.isPending}>
+          Sign In
+        </button>
+        <div className="divider">OR</div>
+        <div className="form-group">
+          <label>Google ID Token</label>
+          <input value={googleToken} onChange={(e) => setGoogleToken(e.target.value)} placeholder="Paste token from Google OAuth flow" />
+        </div>
+        <button onClick={() => googleMutation.mutate()} disabled={googleMutation.isPending}>
+          Sign In with Google Token
+        </button>
+      </section>
+
+      {token && (
+        <section>
+          <div className="actions">
+            <button onClick={handleSelectFile} disabled={uploadMutation.isPending}>
+              {uploadMutation.isPending ? "Uploading..." : "Select Image & Upload"}
+            </button>
+            <button onClick={() => jobsQuery.refetch()} disabled={jobsQuery.isFetching}>
+              Refresh Jobs
+            </button>
+          </div>
+          <h2>Jobs</h2>
+          {jobsQuery.isLoading ? (
+            <p>Loading jobs...</p>
+          ) : (
+            <table>
+              <thead>
+                <tr>
+                  <th>ID</th>
+                  <th>Status</th>
+                  <th>Output</th>
+                  <th>Error</th>
+                </tr>
+              </thead>
+              <tbody>
+                {jobsQuery.data?.map((job) => (
+                  <tr key={job.id}>
+                    <td>{job.id}</td>
+                    <td>{job.status}</td>
+                    <td>
+                      {job.output_path ? (
+                        <button onClick={() => handleDownload(job.id)}>Download</button>
+                      ) : (
+                        "-"
+                      )}
+                    </td>
+                    <td>{job.error_message ?? ""}</td>
+                  </tr>
+                ))}
+              </tbody>
+            </table>
+          )}
+        </section>
+      )}
+    </div>
+  );
+};
+
+export default App;
 
EOF
)
