import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  JobResponse,
  TokenResponse,
  UserProfile,
  WhitelistCheckResponse,
  createApiClient
} from "./api";

const defaultServerUrl =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8000";

type AppPhase = "splash" | "configureServer" | "onboard" | "dashboard";
type OnboardingMode = "new" | "returning";
type RestormerMode = "denoise" | "motion_deblur" | "defocus_deblur";

type LoadingState = {
  message: string;
  progress: number;
  accent?: string;
};

type RegisterFormData = {
  email: string;
  full_name: string;
  password: string;
};

type LoginFormData = {
  email: string;
  password: string;
};

const statusMeta: Record<string, { label: string; tone: string; icon: string }> = {
  queued: { label: "Queued", tone: "tone-queued", icon: "🕑" },
  processing: { label: "Processing", tone: "tone-processing", icon: "⚙️" },
  completed: { label: "Completed", tone: "tone-completed", icon: "✨" },
  failed: { label: "Failed", tone: "tone-failed", icon: "⚠️" }
};

const stageDescriptions: Record<string, string> = {
  queued: "Awaiting GPU availability",
  initialising: "Preparing inference graph",
  preparing: "Loading the source frame",
  loading_models: "Fetching Restormer weights",
  batch_prepare: "Decoding batch imagery",
  restormer_pass: "Executing Restormer inference",
  saving: "Writing processed imagery",
  archiving: "Packaging download archive",
  completed: "Job finished successfully",
  failed: "Job halted due to an error"
};

const restormerOptions: Array<{ value: RestormerMode; label: string; description: string }> = [
  {
    value: "denoise",
    label: "Restormer Denoising",
    description: "Suppress sensor noise while preserving crisp texture."
  },
  {
    value: "motion_deblur",
    label: "Restormer Motion Deblurring",
    description: "Stabilise handheld or action shots affected by motion."
  },
  {
    value: "defocus_deblur",
    label: "Restormer Defocus Deblurring",
    description: "Recover optical focus lost to shallow depth of field."
  }
];

const passOptions = [1, 2, 3, 4, 5] as const;

const illustrationMap: Record<string, string> = {
  queued: "radial-amber",
  processing: "radial-indigo",
  completed: "radial-emerald",
  failed: "radial-rose"
};

const clamp = (value: number) => Math.max(0, Math.min(1, value));
const formatPercent = (value: number) => `${Math.round(clamp(value) * 100)}%`;

const base64ToBlob = (value: string) => {
  const byteCharacters = atob(value);
  const byteNumbers = new Array(byteCharacters.length)
    .fill(0)
    .map((_, idx) => byteCharacters.charCodeAt(idx));
  const byteArray = new Uint8Array(byteNumbers);
  return new Blob([byteArray.buffer]);
};

const getStoredValue = (key: string): string | null => {
  try {
    return localStorage.getItem(key);
  } catch (error) {
    console.warn("storage read failed", error);
    return null;
  }
};

const setStoredValue = (key: string, value: string | null) => {
  try {
    if (value === null) {
      localStorage.removeItem(key);
    } else {
      localStorage.setItem(key, value);
    }
  } catch (error) {
    console.warn("storage write failed", error);
  }
};

const SplashScreen: React.FC<LoadingState> = ({ message, progress, accent }) => (
  <div className="splash-screen">
    <div className={`splash-card ${accent ?? ""}`}>
      <div className="splash-emblem">📸</div>
      <div className="splash-copy">
        <h1>Restormer Remote Studio</h1>
        <p>{message}</p>
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: formatPercent(progress) }} />
      </div>
      <span className="progress-label">{formatPercent(progress)}</span>
    </div>
  </div>
);

const ImageCue: React.FC<{ status: string }> = ({ status }) => {
  const className = `image-cue ${illustrationMap[status] ?? "radial-indigo"}`;
  const meta = statusMeta[status] ?? { icon: "🎞️", label: status, tone: "tone-processing" };
  return (
    <div className={className} title={meta.label}>
      <span aria-hidden="true">{meta.icon}</span>
    </div>
  );
};

const useJobsQuery = (
  apiClient: ReturnType<typeof createApiClient>,
  token: string | null,
  phase: AppPhase,
  serverUrl: string
) =>
  useQuery<JobResponse[], Error>({
    queryKey: ["jobs", token, serverUrl],
    queryFn: async () => {
      if (!token) {
        throw new Error("Not authenticated");
      }
      return apiClient.fetchJobs(token);
    },
    enabled: phase === "dashboard" && Boolean(token),
    refetchInterval: (data) => {
      if (!token || phase !== "dashboard") {
        return false;
      }
      if (data?.some((job) => job.status === "processing" || job.status === "queued")) {
        return 3000;
      }
      return 12000;
    }
  });

const App: React.FC = () => {
  const [phase, setPhase] = useState<AppPhase>("splash");
  const [loadingState, setLoadingState] = useState<LoadingState>({
    message: "Launching GPU cockpit…",
    progress: 0.18
  });

  const [serverUrl, setServerUrl] = useState<string>(() => getStoredValue("restormer.serverUrl") ?? defaultServerUrl);
  const [serverUrlInput, setServerUrlInput] = useState(serverUrl);
  const [serverUrlError, setServerUrlError] = useState<string | null>(null);
  const [serverProbeMessage, setServerProbeMessage] = useState<string>("");
  const [probeBusy, setProbeBusy] = useState(false);

  const [token, setToken] = useState<string | null>(() => getStoredValue("restormer.token"));
  const [profile, setProfile] = useState<UserProfile | null>(null);

  const [onboardingMode, setOnboardingMode] = useState<OnboardingMode>("new");
  const [verification, setVerification] = useState<WhitelistCheckResponse | null>(null);
  const [onboardingError, setOnboardingError] = useState<string | null>(null);

  const [newEmail, setNewEmail] = useState("");
  const [newFullName, setNewFullName] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedMode, setSelectedMode] = useState<RestormerMode>("denoise");
  const [selectedPasses, setSelectedPasses] = useState<number>(1);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [uploadWarning, setUploadWarning] = useState<string | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);

  const apiClient = useMemo(() => createApiClient(serverUrl), [serverUrl]);
  const jobsQuery = useJobsQuery(apiClient, token, phase, serverUrl);

  useEffect(() => {
    setStoredValue("restormer.serverUrl", serverUrl);
  }, [serverUrl]);

  useEffect(() => {
    if (token) {
      setStoredValue("restormer.token", token);
    } else {
      setStoredValue("restormer.token", null);
    }
  }, [token]);

  useEffect(() => {
    if (phase !== "dashboard" || !jobsQuery.data?.length) {
      return;
    }
    if (selectedJobId === null) {
      setSelectedJobId(jobsQuery.data[0]?.id ?? null);
      return;
    }
    const exists = jobsQuery.data.some((job) => job.id === selectedJobId);
    if (!exists) {
      setSelectedJobId(jobsQuery.data[0]?.id ?? null);
    }
  }, [jobsQuery.data, phase, selectedJobId]);

  useEffect(() => {
    const initialise = async () => {
      try {
        setPhase("splash");
        setLoadingState({ message: "Restoring preferences…", progress: 0.22 });
        const storedServer = getStoredValue("restormer.serverUrl") ?? defaultServerUrl;
        setServerUrl(storedServer);
        setServerUrlInput(storedServer);

        const client = createApiClient(storedServer);
        setLoadingState({ message: "Checking server availability…", progress: 0.45 });
        await client.health();

        const storedToken = getStoredValue("restormer.token");
        if (storedToken) {
          setLoadingState({ message: "Verifying session…", progress: 0.65 });
          try {
            const me = await client.fetchProfile(storedToken);
            setToken(storedToken);
            setProfile(me);
            setLoadingState({ message: `Welcome back, ${me.full_name}`, progress: 0.92 });
            setTimeout(() => setPhase("dashboard"), 180);
            return;
          } catch (error) {
            console.warn("Stored session invalid", error);
            setStoredValue("restormer.token", null);
          }
        }
        setLoadingState({ message: "Let’s connect you to the studio", progress: 0.88 });
        setTimeout(() => setPhase("onboard"), 220);
      } catch (error) {
        console.warn("Bootstrap failed", error);
        setServerUrlError("Could not reach the server. Please confirm the URL.");
        setPhase("configureServer");
      }
    };

    initialise();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const verifyWhitelistMutation = useMutation({
    mutationFn: async (email: string) => apiClient.verifyWhitelist(email),
    onSuccess: (response) => {
      setVerification(response);
      setOnboardingError(null);
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : "Unable to check whitelist";
      setOnboardingError(message);
    }
  });

  const registerMutation = useMutation<TokenResponse, Error, RegisterFormData>({
    mutationFn: async (payload) => {
      await apiClient.registerUser(payload);
      return apiClient.loginWithPassword(payload.email, payload.password);
    }
  });

  const loginMutation = useMutation<TokenResponse, Error, LoginFormData>({
    mutationFn: ({ email, password }) => apiClient.loginWithPassword(email, password)
  });

  const handleAuthenticated = useCallback(
    async (accessToken: string) => {
      setPhase("splash");
      setLoadingState({ message: "Securing your studio session…", progress: 0.72 });
      try {
        const me = await apiClient.fetchProfile(accessToken);
        setToken(accessToken);
        setProfile(me);
        setLoadingState({ message: `Hello ${me.full_name}`, progress: 0.98 });
        setTimeout(() => setPhase("dashboard"), 200);
      } catch (error) {
        setLoadingState({ message: "Unable to finish sign-in", progress: 1, accent: "error" });
        setPhase("onboard");
        throw error;
      }
    },
    [apiClient]
  );

  const uploadMutation = useMutation({
    mutationFn: async (formData: FormData) => {
      if (!token) {
        throw new Error("Not authenticated");
      }
      setUploadProgress(0.04);
      await apiClient.uploadJob({
        token,
        data: formData,
        onProgress: (value) => setUploadProgress(clamp(value))
      });
    },
    onSuccess: () => {
      setUploadProgress(1);
      setUploadWarning(null);
      setUploadMessage("Upload complete. Monitoring job queue…");
      void jobsQuery.refetch();
      setTimeout(() => setUploadProgress(0), 700);
    },
    onError: (error: unknown) => {
      console.error(error);
      const message = error instanceof Error ? error.message : "Upload failed";
      setUploadWarning(message);
      setUploadProgress(0);
    }
  });

  const handleSelectFiles = async () => {
    if (uploadMutation.isPending || !token) {
      return;
    }
    const files = await window.electronAPI.openFiles();
    if (!files || files.length === 0) {
      return;
    }
    const trimmed = files.slice(0, 25);
    if (files.length > trimmed.length) {
      setUploadWarning("Only the first 25 images will be queued per batch.");
    } else {
      setUploadWarning(null);
    }
    const option = restormerOptions.find((item) => item.value === selectedMode);
    const label = option?.label ?? selectedMode;
    setUploadMessage(
      `Uploading ${trimmed.length} image${trimmed.length === 1 ? "" : "s"} with ${label} · ${selectedPasses}x passes.`
    );
    const formData = new FormData();
    formData.append("mode", selectedMode);
    formData.append("passes", String(selectedPasses));
    trimmed.forEach((file, index) => {
      const blob = base64ToBlob(file.buffer);
      const filename = file.filePath.split(/[\\/]/).pop() ?? `upload-${index}.png`;
      formData.append("files", blob, filename);
    });
    await uploadMutation.mutateAsync(formData);
  };

  const handleServerProbe = async () => {
    try {
      setProbeBusy(true);
      setServerUrlError(null);
      setServerProbeMessage("Pinging /health…");
      const candidate = serverUrlInput.trim();
      if (!candidate) {
        throw new Error("Server URL is required");
      }
      // eslint-disable-next-line no-new
      new URL(candidate);
      const probeClient = createApiClient(candidate);
      const response = await probeClient.health();
      setServerUrl(candidate);
      if (token) {
        setToken(null);
        setProfile(null);
        setStoredValue("restormer.token", null);
      }
      setServerProbeMessage(
        `Connected to ${candidate} (public base: ${response.public_base_url || "not set"})`
      );
      setTimeout(() => {
        setPhase("onboard");
      }, 200);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to reach server";
      setServerUrlError(message);
      setServerProbeMessage("");
    } finally {
      setProbeBusy(false);
    }
  };

  const handleVerifyAccess = async () => {
    setOnboardingError(null);
    if (!newEmail) {
      setOnboardingError("Enter the email you would like to register with.");
      return;
    }
    await verifyWhitelistMutation.mutateAsync(newEmail);
  };

  const handleRegister = async () => {
    setOnboardingError(null);
    if (!verification?.allowed) {
      setOnboardingError("Verify that your email is whitelisted before registering.");
      return;
    }
    if (!newFullName) {
      setOnboardingError("Please enter your display name.");
      return;
    }
    if (newPassword.length < 8) {
      setOnboardingError("Use a password with at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setOnboardingError("Passwords do not match.");
      return;
    }
    try {
      const tokenResponse = await registerMutation.mutateAsync({
        email: newEmail,
        full_name: newFullName,
        password: newPassword
      });
      await handleAuthenticated(tokenResponse.access_token);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Registration failed";
      setOnboardingError(message);
    }
  };

  const handleLogin = async () => {
    setOnboardingError(null);
    if (!loginEmail || !loginPassword) {
      setOnboardingError("Enter both your email and password.");
      return;
    }
    try {
      const tokenResponse = await loginMutation.mutateAsync({
        email: loginEmail,
        password: loginPassword
      });
      await handleAuthenticated(tokenResponse.access_token);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Sign-in failed";
      setOnboardingError(message);
    }
  };

  const handleLogout = () => {
    setToken(null);
    setProfile(null);
    setStoredValue("restormer.token", null);
    setPhase("onboard");
  };

  const selectedJob = jobsQuery.data?.find((job) => job.id === selectedJobId) ?? null;
  const latestDebug = useMemo(() => {
    if (!jobsQuery.data) {
      return [] as { job: JobResponse; line: string; index: number }[];
    }
    const tail = jobsQuery.data.flatMap((job) =>
      job.debug_lines.slice(-3).map((line, index) => ({ job, line, index }))
    );
    return tail.slice(-15).reverse();
  }, [jobsQuery.data]);

  const renderServerConfigurator = () => (
    <div className="card configure-card">
      <header>
        <div>
          <h2>Connect to your Restormer server</h2>
          <p className="card-subtitle">
            Provide the HTTPS endpoint exposed to the public web. We automatically ping <code>/health</code>
            to confirm connectivity.
          </p>
        </div>
        <ImageCue status="queued" />
      </header>
      <label className="field">
        <span>Public server URL</span>
        <input
          value={serverUrlInput}
          onChange={(event) => setServerUrlInput(event.target.value)}
          placeholder="https://denoise.example.com"
          spellCheck={false}
          autoFocus
        />
      </label>
      {serverUrlError && <p className="error-banner">{serverUrlError}</p>}
      {serverProbeMessage && <p className="success-banner">{serverProbeMessage}</p>}
      <div className="card-actions">
        <button type="button" className="secondary" onClick={() => setServerUrlInput(serverUrl)}>
          Reset
        </button>
        <button type="button" onClick={handleServerProbe} disabled={probeBusy}>
          {probeBusy ? "Checking…" : "Save & Continue"}
        </button>
      </div>
    </div>
  );

  const renderOnboarding = () => (
    <div className="card onboarding-card">
      <header>
        <div>
          <h2>Sign in to the restoration deck</h2>
          <p className="card-subtitle">
            Choose a username and password that we verify against the server whitelist before granting access.
          </p>
        </div>
        <ImageCue status="processing" />
      </header>
      <div className="tabs">
        <button
          className={onboardingMode === "new" ? "active" : ""}
          type="button"
          onClick={() => {
            setOnboardingMode("new");
            setOnboardingError(null);
          }}
        >
          I need an account
        </button>
        <button
          className={onboardingMode === "returning" ? "active" : ""}
          type="button"
          onClick={() => {
            setOnboardingMode("returning");
            setOnboardingError(null);
          }}
        >
          I already have access
        </button>
      </div>
      {onboardingMode === "new" ? (
        <div className="onboarding-grid">
          <div className="field">
            <span>Authorised email</span>
            <input
              value={newEmail}
              onChange={(event) => setNewEmail(event.target.value)}
              placeholder="you@studio.com"
              spellCheck={false}
            />
            <button
              type="button"
              className="link-button"
              onClick={handleVerifyAccess}
              disabled={verifyWhitelistMutation.isPending}
            >
              {verifyWhitelistMutation.isPending ? "Checking whitelist…" : "Check whitelist"}
            </button>
            {verification && (
              <span className={verification.allowed ? "badge-success" : "badge-muted"}>
                {verification.message}
              </span>
            )}
          </div>
          <label className="field">
            <span>Display name</span>
            <input
              value={newFullName}
              onChange={(event) => setNewFullName(event.target.value)}
              placeholder="Ava Operator"
            />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              placeholder="Create a strong password"
            />
          </label>
          <label className="field">
            <span>Confirm password</span>
            <input
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              placeholder="Repeat password"
            />
          </label>
          <div className="card-actions">
            <button type="button" onClick={handleRegister} disabled={registerMutation.isPending}>
              {registerMutation.isPending ? "Creating secure vault…" : "Create my account"}
            </button>
          </div>
        </div>
      ) : (
        <div className="onboarding-grid">
          <label className="field">
            <span>Email</span>
            <input
              value={loginEmail}
              onChange={(event) => setLoginEmail(event.target.value)}
              placeholder="you@studio.com"
              spellCheck={false}
            />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={loginPassword}
              onChange={(event) => setLoginPassword(event.target.value)}
              placeholder="Enter password"
            />
          </label>
          <div className="card-actions">
            <button type="button" onClick={handleLogin} disabled={loginMutation.isPending}>
              {loginMutation.isPending ? "Authenticating…" : "Sign in"}
            </button>
          </div>
        </div>
      )}
      {onboardingError && <p className="error-banner">{onboardingError}</p>}
      <p className="helper-text">
        Tip: if you hit disk space issues during install, free ~2 GB for Electron dependencies before rerunning
        <code>npm install</code>.
      </p>
    </div>
  );

  const renderDashboard = () => (
    <div className="dashboard">
      <header className="dashboard-header">
        <div>
          <h1>✨ Ultra-fine restoration cockpit</h1>
          <p>
            Connected to <strong>{serverUrl}</strong> as {profile?.full_name ?? "anonymous operator"}. GPU jobs
            auto-scale and stream debug telemetry in real time.
          </p>
        </div>
        <div className="header-actions">
          <button type="button" className="secondary" onClick={() => setPhase("configureServer")}>
            Reconfigure server
          </button>
          <button type="button" className="ghost" onClick={handleLogout}>
            Log out
          </button>
        </div>
      </header>

      <section className="dashboard-grid">
        <article className="card actions-card">
          <header>
            <div>
              <h2>Submit new imagery</h2>
              <p className="card-subtitle">
                We stream upload progress and GPU stage updates so you always know what the pipeline is doing.
              </p>
            </div>
            <ImageCue status="processing" />
          </header>
          <div className="mode-controls">
            <label className="field compact">
              <span>Restormer function</span>
              <select
                value={selectedMode}
                onChange={(event) => setSelectedMode(event.target.value as RestormerMode)}
              >
                {restormerOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field compact">
              <span>Passes</span>
              <select
                value={selectedPasses}
                onChange={(event) => setSelectedPasses(Number(event.target.value) || 1)}
              >
                {passOptions.map((value) => (
                  <option key={value} value={value}>
                    {value}x
                  </option>
                ))}
              </select>
            </label>
          </div>
          <p className="helper-text">
            {restormerOptions.find((option) => option.value === selectedMode)?.description}
          </p>
          <div className="actions">
            <button type="button" onClick={handleSelectFiles} disabled={uploadMutation.isPending || !token}>
              {uploadMutation.isPending ? "Uploading…" : "Select files & upload"}
            </button>
            <button type="button" className="secondary" onClick={() => jobsQuery.refetch()}>
              Refresh jobs
            </button>
          </div>
          <div className="progress-track subtle">
            <div className="progress-fill" style={{ width: formatPercent(uploadProgress) }} />
          </div>
          <span className="progress-label">{uploadMutation.isPending ? formatPercent(uploadProgress) : "Idle"}</span>
          {uploadMessage && <p className="helper-text emphasis">{uploadMessage}</p>}
          {uploadWarning && <p className="warning-banner">{uploadWarning}</p>}
          {jobsQuery.isFetching && <span className="fetch-indicator">Syncing job telemetry…</span>}
        </article>

        <article className="card debug-card">
          <header>
            <div>
              <h2>Active debugging feed</h2>
              <p className="card-subtitle">Live tail of GPU pipeline messages and automation cues.</p>
            </div>
            <ImageCue status="completed" />
          </header>
          <div className="debug-stream">
            {latestDebug.length === 0 ? (
              <p className="empty-state">Submit a job to populate debug telemetry.</p>
            ) : (
              latestDebug.map(({ job, line, index }) => (
                <div key={`${job.id}-${index}-${line}`} className={`debug-line ${statusMeta[job.status]?.tone ?? ""}`}>
                  <span className="debug-job">Job #{job.id}</span>
                  <span className="debug-text">{line}</span>
                </div>
              ))
            )}
          </div>
        </article>

        <article className="card jobs-card">
          <header>
            <div>
              <h2>Job timeline</h2>
              <p className="card-subtitle">Monitor Restormer batches with live telemetry.</p>
            </div>
            <ImageCue status="queued" />
          </header>
          {jobsQuery.isLoading ? (
            <p className="empty-state">Loading jobs…</p>
          ) : jobsQuery.isError ? (
            <p className="error-banner">
              Unable to load jobs: {jobsQuery.error instanceof Error ? jobsQuery.error.message : "Unknown error"}
            </p>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Status</th>
                    <th>Stage</th>
                    <th>Function</th>
                    <th>Passes</th>
                    <th>Images</th>
                    <th>Progress</th>
                    <th>Filename</th>
                    <th>Download</th>
                  </tr>
                </thead>
                <tbody>
                  {jobsQuery.data && jobsQuery.data.length === 0 && (
                    <tr>
                      <td colSpan={9} className="empty-state">
                        No jobs yet — upload imagery to kick off the pipeline.
                      </td>
                    </tr>
                  )}
                  {jobsQuery.data?.map((job) => {
                    const meta = statusMeta[job.status] ?? statusMeta.processing;
                    return (
                      <tr
                        key={job.id}
                        className={selectedJob?.id === job.id ? "row-active" : ""}
                        onClick={() => setSelectedJobId(job.id)}
                      >
                        <td>#{job.id}</td>
                        <td>
                          <div className={`status-chip ${meta.tone}`}>
                            <span aria-hidden="true">{meta.icon}</span>
                            {meta.label}
                          </div>
                        </td>
                        <td>
                          <span className="stage-label">{stageDescriptions[job.stage] ?? job.stage}</span>
                        </td>
                        <td>{job.mode_label}</td>
                        <td>{job.passes}x</td>
                        <td>{job.file_count}</td>
                        <td className="progress-cell">
                          <div className="progress-track subtle">
                            <div className="progress-fill" style={{ width: formatPercent(job.progress) }} />
                          </div>
                          <span className="progress-label">{formatPercent(job.progress)}</span>
                        </td>
                        <td className="filename-cell">{job.filename}</td>
                        <td>
                          {job.downloadable ? (
                            <div className="download-actions">
                              <button type="button" onClick={() => token && apiClient.downloadProcessedImage(token, job.id)}>
                                Save
                              </button>
                              {job.download_url && (
                                <a href={job.download_url} target="_blank" rel="noreferrer">
                                  Open link
                                </a>
                              )}
                            </div>
                          ) : (
                            <span className="muted">Pending</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </article>

        <article className="card job-detail-card">
          <header>
            <div>
              <h2>Job diagnostics</h2>
              <p className="card-subtitle">
                Detailed debugging stream, including errors and recovery hints for the selected job.
              </p>
            </div>
            <ImageCue status={selectedJob?.status ?? "processing"} />
          </header>
          {selectedJob ? (
              <div className="job-detail">
                <h3>
                  Job #{selectedJob.id} · {stageDescriptions[selectedJob.stage] ?? selectedJob.stage}
                </h3>
                <div className="progress-track subtle">
                  <div className="progress-fill" style={{ width: formatPercent(selectedJob.progress) }} />
                </div>
                <span className="progress-label">{formatPercent(selectedJob.progress)}</span>
                <div className="job-meta-grid">
                  <div>
                    <span className="meta-label">Function</span>
                    <span className="meta-value">{selectedJob.mode_label}</span>
                  </div>
                  <div>
                    <span className="meta-label">Passes</span>
                    <span className="meta-value">{selectedJob.passes}×</span>
                  </div>
                  <div>
                    <span className="meta-label">Images</span>
                    <span className="meta-value">{selectedJob.file_count}</span>
                  </div>
                </div>
                <div className="job-files-grid">
                  <div>
                    <h4>Input files</h4>
                    {selectedJob.input_files.length === 0 ? (
                      <p className="muted">Files pending upload.</p>
                    ) : (
                      <ul>
                        {selectedJob.input_files.map((name) => (
                          <li key={`input-${selectedJob.id}-${name}`}>{name}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                  <div>
                    <h4>Output files</h4>
                    {selectedJob.output_files.length === 0 ? (
                      <p className="muted">Outputs become available once the batch finishes.</p>
                    ) : (
                      <ul>
                        {selectedJob.output_files.map((name) => (
                          <li key={`output-${selectedJob.id}-${name}`}>{name}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
                {selectedJob.error_message && <p className="error-banner">{selectedJob.error_message}</p>}
                <ul className="debug-list">
                  {selectedJob.debug_lines.map((line, index) => (
                    <li key={`${selectedJob.id}-${index}-${line}`}>{line}</li>
                  ))}
              </ul>
            </div>
          ) : (
            <p className="empty-state">Select a job from the timeline to inspect debug messages.</p>
          )}
        </article>
      </section>
    </div>
  );

  return (
    <div className="app-root">
      <div className="app-gradient" />
      {phase === "splash" ? (
        <SplashScreen {...loadingState} />
      ) : (
        <div className="app-shell">
          {phase === "configureServer" && renderServerConfigurator()}
          {phase === "onboard" && (
            <>
              {renderServerConfigurator()}
              {renderOnboarding()}
            </>
          )}
          {phase === "dashboard" && renderDashboard()}
        </div>
      )}
    </div>
  );
};

export default App;
