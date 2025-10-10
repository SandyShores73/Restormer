<<<<<<< HEAD
import axios from "axios";

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface JobResponse {
  id: number;
  status: string;
  filename: string;
  created_at: string;
  updated_at: string;
  error_message: string | null;
  downloadable: boolean;
  download_path: string | null;
  download_url: string | null;
}

export interface ApiClient {
  loginWithPassword: (username: string, password: string) => Promise<TokenResponse>;
  loginWithGoogle: (idToken: string) => Promise<TokenResponse>;
  uploadJob: (params: { token: string; data: FormData }) => Promise<void>;
  fetchJobs: (token: string) => Promise<JobResponse[]>;
  downloadProcessedImage: (token: string, jobId: number) => Promise<void>;
}

const buildBaseURL = (baseUrl: string) => baseUrl.replace(/\/+$/, "");

export const createApiClient = (baseUrl: string): ApiClient => {
  const normalisedBase = buildBaseURL(baseUrl);
  const http = axios.create({ baseURL: normalisedBase });

  return {
    loginWithPassword: async (username: string, password: string) => {
      const params = new URLSearchParams();
      params.append("username", username);
      params.append("password", password);
      params.append("grant_type", "password");
      const { data } = await http.post("/token", params, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" }
      });
      return data;
    },
    loginWithGoogle: async (idToken: string) => {
      const { data } = await http.post("/oauth/google", { token: idToken });
      return data;
    },
    uploadJob: async ({ token, data }) => {
      await http.post("/jobs", data, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "multipart/form-data"
        }
      });
    },
    fetchJobs: async (token: string) => {
      const { data } = await http.get<JobResponse[]>("/jobs", {
        headers: { Authorization: `Bearer ${token}` }
      });
      return data;
    },
    downloadProcessedImage: async (token: string, jobId: number) => {
      const { data, headers } = await http.get(`/jobs/${jobId}/download`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: "blob"
      });
      const disposition = headers["content-disposition"];
      const filenameMatch = disposition?.match(/filename="?(.+?)"?$/);
      const filename = filenameMatch ? filenameMatch[1] : `processed-${jobId}.png`;
      const url = window.URL.createObjectURL(new Blob([data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      window.URL.revokeObjectURL(url);
    }
  };
};
=======
 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a//dev/null b/client/src/api.ts
index 0000000000000000000000000000000000000000..1df93fe579b15fdbaa4d7c8741e19a53f6f57184 100644
--- a//dev/null
+++ b/client/src/api.ts
@@ -0,0 +1,63 @@
+import axios from "axios";
+
+const API_BASE = process.env.VITE_API_BASE ?? "http://localhost:8000";
+
+export interface TokenResponse {
+  access_token: string;
+  token_type: string;
+}
+
+export interface JobResponse {
+  id: number;
+  status: string;
+  output_path: string | null;
+  error_message: string | null;
+}
+
+export const loginWithPassword = async (username: string, password: string): Promise<TokenResponse> => {
+  const params = new URLSearchParams();
+  params.append("username", username);
+  params.append("password", password);
+  params.append("grant_type", "password");
+  const { data } = await axios.post(`${API_BASE}/token`, params, {
+    headers: { "Content-Type": "application/x-www-form-urlencoded" }
+  });
+  return data;
+};
+
+export const loginWithGoogle = async (idToken: string): Promise<TokenResponse> => {
+  const { data } = await axios.post(`${API_BASE}/oauth/google`, { token: idToken });
+  return data;
+};
+
+export const uploadJob = async ({ token, data }: { token: string; data: FormData }) => {
+  await axios.post(`${API_BASE}/jobs`, data, {
+    headers: {
+      Authorization: `Bearer ${token}`,
+      "Content-Type": "multipart/form-data"
+    }
+  });
+};
+
+export const fetchJobs = async (token: string): Promise<JobResponse[]> => {
+  const { data } = await axios.get(`${API_BASE}/jobs`, {
+    headers: { Authorization: `Bearer ${token}` }
+  });
+  return data;
+};
+
+export const downloadProcessedImage = async (token: string, jobId: number) => {
+  const { data, headers } = await axios.get(`${API_BASE}/jobs/${jobId}/download`, {
+    headers: { Authorization: `Bearer ${token}` },
+    responseType: "blob"
+  });
+  const disposition = headers["content-disposition"];
+  const filenameMatch = disposition?.match(/filename="?(.+?)"?$/);
+  const filename = filenameMatch ? filenameMatch[1] : `processed-${jobId}.png`;
+  const url = window.URL.createObjectURL(new Blob([data]));
+  const a = document.createElement("a");
+  a.href = url;
+  a.download = filename;
+  a.click();
+  window.URL.revokeObjectURL(url);
+};
 
EOF
)
>>>>>>> origin/main
