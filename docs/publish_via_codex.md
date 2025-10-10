 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/docs/publish_via_codex.md
index 0000000000000000000000000000000000000000..01537ab9b2b250d57dfd0e133243a49606db4309 100644
--- a//dev/null
+++ b/docs/publish_via_codex.md
@@ -0,0 +1,77 @@
+# Publishing the Restormer Suite via Codex
+
+The repository can be published to a Codex workspace so that the server and
+client artifacts are versioned and distributed from a single release.  The
+instructions below assume you have access to the Codex CLI and an organisation
+project that allows publishing desktop and backend artifacts.
+
+## Prerequisites
+
+1. Install the Codex CLI on the Windows 11 workstation that will host the
+   backend (replace the download URL with the one provided by your Codex
+   administrator):
+   ```powershell
+   iwr https://download.codex.example.com/cli/latest/windows -OutFile codex.exe
+   ```
+2. Authenticate the CLI with your Codex account:
+   ```powershell
+   .\codex.exe login
+   ```
+3. Ensure the server build artifacts (`RestormerServer.exe` and
+   `RestormerServerInstaller.exe`) and the Electron client installers are
+   generated following the steps in `server/README.md` and `client/README.md`.
+
+## Project Manifest
+
+Create a `codex.yaml` file at the repository root to describe the publishable
+artifacts and metadata.  A basic example is shown below:
+
+```yaml
+name: restormer-remote-suite
+version: 1.0.0
+summary: GPU-enabled remote denoise, detail refinement, and focus correction suite
+artifacts:
+  server:
+    path: server/dist/RestormerServerInstaller.exe
+    platform: windows-x64
+  client-windows:
+    path: client/dist/RestormerClientSetup.exe
+    platform: windows-x64
+  client-macos:
+    path: client/dist/RestormerClient.dmg
+    platform: macos-x64
+release_notes: docs/release-notes.md
+```
+
+Update the `version` and artifact paths each time you produce a new build.
+Optional fields (such as `tags`, `channels`, or `dependencies`) can be added if
+required by your Codex deployment.
+
+## Publishing Steps
+
+1. Validate the manifest and artifacts:
+   ```powershell
+   .\codex.exe validate codex.yaml
+   ```
+2. Publish the release to the default channel:
+   ```powershell
+   .\codex.exe publish codex.yaml --channel stable
+   ```
+3. (Optional) Promote the same build to a beta or canary channel for staged
+   rollouts:
+   ```powershell
+   .\codex.exe promote restormer-remote-suite 1.0.0 --from stable --to beta
+   ```
+4. Confirm the release is visible in the Codex dashboard and share the download
+   links with authorised users.
+
+## Automation Tips
+
+- Integrate `codex.exe publish` into your CI pipeline after the build steps.
+- Use the `--notes` flag to override release notes without modifying
+  `codex.yaml`.
+- Combine `codex.exe promote` with scripted smoke tests to automatically push
+  builds to stable once verification passes.
+
+Refer to your Codex administrator for environment-specific flags or single sign
+on requirements.
 
EOF
)
