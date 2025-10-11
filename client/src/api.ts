import axios from "axios";

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface JobResponse {
  id: number;
  status: string;
  stage: string;
  filename: string;
  mode: string;
  mode_label: string;
  passes: number;
  file_count: number;
  input_files: string[];
  output_files: string[];
  created_at: string;
  updated_at: string;
  error_message: string | null;
  downloadable: boolean;
  download_path: string | null;
  download_url: string | null;
  progress: number;
  debug_lines: string[];
}

export interface UserProfile {
  id: number;
  email: string;
  full_name: string;
}

export interface WhitelistCheckResponse {
  allowed: boolean;
  display_name: string | null;
  message: string;
}

export interface RegisterUserPayload {
  email: string;
  full_name: string;
  password: string;
}

export interface HealthResponse {
  status: string;
  public_base_url: string;
}

export interface UploadJobParams {
  token: string;
  data: FormData;
  onProgress?: (progress: number) => void;
}

export interface ApiClient {
  loginWithPassword: (username: string, password: string) => Promise<TokenResponse>;
  loginWithGoogle: (idToken: string) => Promise<TokenResponse>;
  uploadJob: (params: UploadJobParams) => Promise<void>;
  fetchJobs: (token: string) => Promise<JobResponse[]>;
  downloadProcessedImage: (token: string, jobId: number) => Promise<void>;
  verifyWhitelist: (email: string) => Promise<WhitelistCheckResponse>;
  registerUser: (payload: RegisterUserPayload) => Promise<UserProfile>;
  fetchProfile: (token: string) => Promise<UserProfile>;
  health: () => Promise<HealthResponse>;
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
    uploadJob: async ({ token, data, onProgress }) => {
      await http.post("/jobs", data, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "multipart/form-data"
        },
        onUploadProgress: (event) => {
          if (!onProgress || !event.total) {
            return;
          }
          onProgress(event.loaded / event.total);
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
    },
    verifyWhitelist: async (email: string) => {
      const { data } = await http.post<WhitelistCheckResponse>("/users/verify", { email });
      return data;
    },
    registerUser: async (payload: RegisterUserPayload) => {
      const { data } = await http.post<UserProfile>("/users", payload);
      return data;
    },
    fetchProfile: async (token: string) => {
      const { data } = await http.get<UserProfile>("/me", {
        headers: { Authorization: `Bearer ${token}` }
      });
      return data;
    },
    health: async () => {
      const { data } = await http.get<HealthResponse>("/health");
      return data;
    }
  };
};
