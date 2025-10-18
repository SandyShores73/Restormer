import React, { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { useMutation, useQuery } from "@tanstack/react-query";

import {
  DiagnosticsLogResponse,
  JobResponse,
  TokenResponse,
  UserProfile,
  WhitelistCheckResponse,
  createApiClient
} from "./api";
import { DebugEvent, debug, debugBus } from "./debug";
import lumaLogo from "./assets/luma-logo.svg";

const defaultServerUrl =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8000";

const HEALTH_CHECK_TIMEOUT = 8000;

type AppPhase = "splash" | "configureServer" | "onboard" | "dashboard";
type OnboardingMode = "new" | "returning";
type PipelineMode = "denoise" | "motion_deblur" | "defocus_deblur";

type LoadingState = {
  message: string;
  progress: number;
  accent?: string;
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
  loading_models: "Fetching model weights",
  batch_prepare: "Decoding batch imagery",
  restormer_pass: "Executing Luma inference",
  saving: "Writing processed imagery",
  archiving: "Packaging download archive",
  completed: "Job finished successfully",
  failed: "Job halted due to an error"
};

const pipelineOptions: Array<{ value: PipelineMode; label: string; description: string }> = [
  {
    value: "denoise",
    label: "Luma Denoising",
    description: "Suppress sensor noise while preserving crisp texture."
  },
  {
    value: "motion_deblur",
    label: "Luma Motion Deblurring",
    description: "Stabilise handheld or action shots affected by motion."
  },
  {
    value: "defocus_deblur",
    label: "Luma Defocus Deblurring",
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
  const bytes = atob(value);
  const buffer = new Uint8Array(bytes.length);
  for (let index = 0; index < bytes.length; index += 1) {
    buffer[index] = bytes.charCodeAt(index);
  }
  return new Blob([buffer.buffer]);
};

const safeRead = (key: string): string | null => {
  try {
    return localStorage.getItem(key);
  } catch (error) {
    debug.warn("storage.read", "Unable to access localStorage", error);
    return null;
  }
};

const safeWrite = (key: string, value: string | null) => {
  try {
    if (value === null) {
      localStorage.removeItem(key);
    } else {
      localStorage.setItem(key, value);
    }
  } catch (error) {
    debug.warn("storage.write", "Unable to persist localStorage entry", { key, error });
  }
};

const extractErrorMessage = (error: unknown, fallback: string) => {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail.trim().length > 0) {
      return detail;
    }
    return error.message || fallback;
  }
  return error instanceof Error ? error.message : fallback;
};

const formatTimestamp = (value: number) =>
  new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

const formatDebugDetail = (detail: unknown) => {
  if (detail === undefined || detail === null) {
    return "";
  }
  if (typeof detail === "string") {
    return detail;
  }
  try {
    return JSON.stringify(detail, null, 2);
  } catch (error) {
    debug.warn("debug.serialise", "Failed to serialise debug detail", error);
    return String(detail);
  }
};

const SplashScreen: React.FC<LoadingState> = ({ message, progress, accent }) => (
  <div className="splash-screen">
    <div className={`splash-card ${accent ?? ""}`}>
      <div className="splash-emblem">
        <img src={lumaLogo} alt="Luma" />
      </div>
      <div className="splash-copy">
        <h1>Luma Studio</h1>
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

type ServerConfiguratorProps = {
  serverUrl: string;
  inputValue: string;
  error: string | null;
  message: string;
  busy: boolean;
  onInput: (value: string) => void;
  onReset: () => void;
  onSubmit: () => void;
};

const ServerConfigurator: React.FC<ServerConfiguratorProps> = ({
  serverUrl,
  inputValue,
  error,
  message,
  busy,
  onInput,
  onReset,
  onSubmit
}) => (
  <div className="card configure-card">
    <header>
      <div>
        <h2>Connect to your Luma server</h2>
        <p className="card-subtitle">
          Provide the HTTPS endpoint exposed to the public web. We automatically ping <code>/health</code> to confirm
          connectivity.
        </p>
      </div>
      <ImageCue status="queued" />
    </header>
    <label className="field">
      <span>Public server URL</span>
      <input
        value={inputValue}
        onChange={(event) => onInput(event.target.value)}
        placeholder="https://denoise.example.com"
        spellCheck={false}
        autoFocus
      />
    </label>
    {error && <p className="error-banner">{error}</p>}
    {message && <p className="success-banner">{message}</p>}
    <div className="card-actions">
      <button type="button" className="secondary" onClick={onReset}>
        Reset to {serverUrl}
      </button>
      <button type="button" onClick={onSubmit} disabled={busy}>
        {busy ? "Checking…" : "Save & Continue"}
      </button>
    </div>
  </div>
);

type OnboardingPanelProps = {
  mode: OnboardingMode;
  verification: WhitelistCheckResponse | null;
  onboardingError: string | null;
  newEmail: string;
  newFullName: string;
  newPassword: string;
  confirmPassword: string;
  loginEmail: string;
  loginPassword: string;
  onModeChange: (mode: OnboardingMode) => void;
  onEmailChange: (value: string) => void;
  onFullNameChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onConfirmPasswordChange: (value: string) => void;
  onLoginEmailChange: (value: string) => void;
  onLoginPasswordChange: (value: string) => void;
  onVerifyAccess: () => Promise<void>;
  onRegister: () => Promise<void>;
  onLogin: () => Promise<void>;
  verifying: boolean;
  registering: boolean;
  loggingIn: boolean;
};

const OnboardingPanel: React.FC<OnboardingPanelProps> = ({
  mode,
  verification,
  onboardingError,
  newEmail,
  newFullName,
  newPassword,
  confirmPassword,
  loginEmail,
  loginPassword,
  onModeChange,
  onEmailChange,
  onFullNameChange,
  onPasswordChange,
  onConfirmPasswordChange,
  onLoginEmailChange,
  onLoginPasswordChange,
  onVerifyAccess,
  onRegister,
  onLogin,
  verifying,
  registering,
  loggingIn
}) => (
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
        className={mode === "new" ? "active" : ""}
        type="button"
        onClick={() => onModeChange("new")}
      >
        I need an account
      </button>
      <button
        className={mode === "returning" ? "active" : ""}
        type="button"
        onClick={() => onModeChange("returning")}
      >
        I already have access
      </button>
    </div>
    {mode === "new" ? (
      <div className="onboarding-grid">
        <div className="field">
          <span>Authorised email</span>
          <input
            value={newEmail}
            onChange={(event) => onEmailChange(event.target.value)}
            placeholder="you@studio.com"
            spellCheck={false}
          />
          <button type="button" className="link-button" onClick={() => void onVerifyAccess()} disabled={verifying}>
            {verifying ? "Checking whitelist…" : "Check whitelist"}
          </button>
          {verification && (
            <span className={verification.allowed ? "badge-success" : "badge-muted"}>{verification.message}</span>
          )}
        </div>
        <label className="field">
          <span>Display name</span>
          <input
            value={newFullName}
            onChange={(event) => onFullNameChange(event.target.value)}
            placeholder="Ava Operator"
          />
        </label>
        <label className="field">
          <span>Password</span>
          <input
            type="password"
            value={newPassword}
            onChange={(event) => onPasswordChange(event.target.value)}
            placeholder="Create a strong password"
          />
        </label>
        <label className="field">
          <span>Confirm password</span>
          <input
            type="password"
            value={confirmPassword}
            onChange={(event) => onConfirmPasswordChange(event.target.value)}
            placeholder="Repeat password"
          />
        </label>
        <div className="card-actions">
          <button type="button" onClick={() => void onRegister()} disabled={registering}>
            {registering ? "Creating secure vault…" : "Create my account"}
          </button>
        </div>
      </div>
    ) : (
      <div className="onboarding-grid">
        <label className="field">
          <span>Email</span>
          <input
            value={loginEmail}
            onChange={(event) => onLoginEmailChange(event.target.value)}
            placeholder="you@studio.com"
            spellCheck={false}
          />
        </label>
        <label className="field">
          <span>Password</span>
          <input
            type="password"
            value={loginPassword}
            onChange={(event) => onLoginPasswordChange(event.target.value)}
            placeholder="Enter password"
          />
        </label>
        <div className="card-actions">
          <button type="button" onClick={() => void onLogin()} disabled={loggingIn}>
            {loggingIn ? "Authenticating…" : "Sign in"}
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

type UploadPanelProps = {
  selectedMode: PipelineMode;
  onModeChange: (value: PipelineMode) => void;
  selectedPasses: number;
  onPassChange: (value: number) => void;
  onSelectFiles: () => void | Promise<void>;
  uploadProgress: number;
  uploadMessage: string | null;
  uploadWarning: string | null;
  uploadDisabled: boolean;
};

const UploadPanel: React.FC<UploadPanelProps> = ({
  selectedMode,
  onModeChange,
  selectedPasses,
  onPassChange,
  onSelectFiles,
  uploadProgress,
  uploadMessage,
  uploadWarning,
  uploadDisabled
}) => (
  <article className="card upload-card">
    <header>
      <div>
        <h2>Queue restoration batch</h2>
        <p className="card-subtitle">Upload imagery to process with the GPU pipeline.</p>
      </div>
      <ImageCue status="processing" />
    </header>
    <div className="upload-grid">
      <div>
        <span className="field-label">Choose pipeline</span>
        <div className="option-grid">
          {pipelineOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              className={`option-tile ${selectedMode === option.value ? "active" : ""}`}
              onClick={() => onModeChange(option.value)}
            >
              <strong>{option.label}</strong>
              <span>{option.description}</span>
            </button>
          ))}
        </div>
      </div>
      <div>
        <span className="field-label">Passes</span>
        <div className="pass-list">
          {passOptions.map((value) => (
            <button
              key={value}
              type="button"
              className={selectedPasses === value ? "active" : ""}
              onClick={() => onPassChange(value)}
            >
              {value}x
            </button>
          ))}
        </div>
      </div>
    </div>
    <div className="card-actions">
      <button type="button" onClick={onSelectFiles} disabled={uploadDisabled}>
        {uploadDisabled ? "Uploading…" : "Select images"}
      </button>
    </div>
    {uploadMessage && <p className="success-banner">{uploadMessage}</p>}
    {uploadWarning && <p className="error-banner">{uploadWarning}</p>}
    {uploadProgress > 0 && (
      <div className="progress-track subtle">
        <div className="progress-fill" style={{ width: formatPercent(uploadProgress) }} />
      </div>
    )}
  </article>
);

type JobTimelineProps = {
  jobs: JobResponse[];
  selectedJobId: number | null;
  onSelectJob: (jobId: number) => void;
  jobsQueryState: ReturnType<typeof useJobsQuery>;
  token: string | null;
  onDownload: (jobId: number) => void;
};

const JobTimeline: React.FC<JobTimelineProps> = ({
  jobs,
  selectedJobId,
  onSelectJob,
  jobsQueryState,
  token,
  onDownload
}) => {
  if (jobsQueryState.isLoading) {
    return (
      <article className="card jobs-card">
        <header>
          <div>
            <h2>Job timeline</h2>
            <p className="card-subtitle">Monitor Luma batches with live telemetry.</p>
          </div>
          <ImageCue status="queued" />
        </header>
        <p className="empty-state">Loading jobs…</p>
      </article>
    );
  }

  if (jobsQueryState.isError) {
    const message = jobsQueryState.error instanceof Error ? jobsQueryState.error.message : "Unknown error";
    return (
      <article className="card jobs-card">
        <header>
          <div>
            <h2>Job timeline</h2>
            <p className="card-subtitle">Monitor Luma batches with live telemetry.</p>
          </div>
          <ImageCue status="failed" />
        </header>
        <p className="error-banner">Unable to load jobs: {message}</p>
      </article>
    );
  }

  return (
    <article className="card jobs-card">
      <header>
        <div>
          <h2>Job timeline</h2>
          <p className="card-subtitle">Monitor Luma batches with live telemetry.</p>
        </div>
        <ImageCue status="queued" />
      </header>
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
            {jobs.length === 0 ? (
              <tr>
                <td colSpan={9} className="empty-state">
                  No jobs yet — upload imagery to kick off the pipeline.
                </td>
              </tr>
            ) : (
              jobs.map((job) => {
                const meta = statusMeta[job.status] ?? statusMeta.processing;
                return (
                  <tr
                    key={job.id}
                    className={selectedJobId === job.id ? "row-active" : ""}
                    onClick={() => onSelectJob(job.id)}
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
                          <button type="button" onClick={() => token && onDownload(job.id)}>
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
              })
            )}
          </tbody>
        </table>
      </div>
    </article>
  );
};

type DebugFeedProps = {
  latestDebug: { job: JobResponse; line: string; index: number }[];
};

const DebugFeed: React.FC<DebugFeedProps> = ({ latestDebug }) => (
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
);

type JobDetailProps = {
  job: JobResponse | null;
};

const JobDetail: React.FC<JobDetailProps> = ({ job }) => (
  <article className="card job-detail-card">
    <header>
      <div>
        <h2>Job diagnostics</h2>
        <p className="card-subtitle">Detailed debugging stream, including errors and recovery hints for the selected job.</p>
      </div>
      <ImageCue status={job?.status ?? "processing"} />
    </header>
    {job ? (
      <div className="job-detail">
        <h3>
          Job #{job.id} · {stageDescriptions[job.stage] ?? job.stage}
        </h3>
        <div className="progress-track subtle">
          <div className="progress-fill" style={{ width: formatPercent(job.progress) }} />
        </div>
        <span className="progress-label">{formatPercent(job.progress)}</span>
        <div className="job-meta-grid">
          <div>
            <span className="meta-label">Function</span>
            <span className="meta-value">{job.mode_label}</span>
          </div>
          <div>
            <span className="meta-label">Passes</span>
            <span className="meta-value">{job.passes}×</span>
          </div>
          <div>
            <span className="meta-label">Images</span>
            <span className="meta-value">{job.file_count}</span>
          </div>
        </div>
        <div className="job-files-grid">
          <div>
            <h4>Input files</h4>
            {job.input_files.length === 0 ? (
              <p className="muted">Files pending upload.</p>
            ) : (
              <ul>
                {job.input_files.map((name) => (
                  <li key={`input-${job.id}-${name}`}>{name}</li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <h4>Output files</h4>
            {job.output_files.length === 0 ? (
              <p className="muted">Outputs become available once the batch finishes.</p>
            ) : (
              <ul>
                {job.output_files.map((name) => (
                  <li key={`output-${job.id}-${name}`}>{name}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
        {job.error_message && <p className="error-banner">{job.error_message}</p>}
        <ul className="debug-list">
          {job.debug_lines.map((line, index) => (
            <li key={`${job.id}-${index}-${line}`}>{line}</li>
          ))}
        </ul>
      </div>
    ) : (
      <p className="empty-state">Select a job from the timeline to inspect debug messages.</p>
    )}
  </article>
);

type DashboardProps = {
  profile: UserProfile;
  onLogout: () => void;
  uploadState: UploadPanelProps;
  jobs: JobResponse[];
  selectedJob: JobResponse | null;
  onSelectJob: (jobId: number) => void;
  jobsQueryState: ReturnType<typeof useJobsQuery>;
  latestDebug: { job: JobResponse; line: string; index: number }[];
  token: string | null;
  onDownload: (jobId: number) => void;
};

const Dashboard: React.FC<DashboardProps> = ({
  profile,
  onLogout,
  uploadState,
  jobs,
  selectedJob,
  onSelectJob,
  jobsQueryState,
  latestDebug,
  token,
  onDownload
}) => (
  <div className="dashboard">
    <header className="dashboard-header">
      <div>
        <h1>✨ Luma control center</h1>
        <p>
          Welcome back, {profile.full_name}. Submit fresh captures for denoising or deburring and monitor the GPU pipeline in
          real time.
        </p>
      </div>
      <div className="profile-chip">
        <span>{profile.full_name}</span>
        <button type="button" className="secondary" onClick={onLogout}>
          Sign out
        </button>
      </div>
    </header>
    <section className="dashboard-grid">
      <UploadPanel {...uploadState} />
      <DebugFeed latestDebug={latestDebug} />
      <JobTimeline
        jobs={jobs}
        selectedJobId={selectedJob?.id ?? null}
        onSelectJob={onSelectJob}
        jobsQueryState={jobsQueryState}
        token={token}
        onDownload={onDownload}
      />
      <JobDetail job={selectedJob} />
    </section>
  </div>
);

type DebugPanelProps = {
  open: boolean;
  events: DebugEvent[];
  onToggle: () => void;
  onClear: () => void;
  onFetchLogs: () => void;
  loading: boolean;
  token: string | null;
  serverLogs: DiagnosticsLogResponse | null;
  serverLogsError: string | null;
};

const DebugPanelOverlay: React.FC<DebugPanelProps> = ({
  open,
  events,
  onToggle,
  onClear,
  onFetchLogs,
  loading,
  token,
  serverLogs,
  serverLogsError
}) => (
  <>
    <button type="button" className="debug-toggle" onClick={onToggle}>
      {open ? "Hide diagnostics" : "Show diagnostics"}
    </button>
    {open && (
      <aside className="debug-panel">
        <header className="debug-panel-header">
          <div>
            <h3>Diagnostics console</h3>
            <p className="helper-text">Latest renderer events and backend logs.</p>
          </div>
          <div className="debug-panel-actions">
            <button type="button" className="secondary" onClick={onClear}>
              Clear events
            </button>
            <button type="button" onClick={onFetchLogs} disabled={loading || !token}>
              {loading ? "Loading…" : "Refresh server logs"}
            </button>
          </div>
        </header>
        <section className="debug-section">
          <h4>Renderer events</h4>
          <div className="debug-event-list">
            {events.length === 0 ? (
              <p className="empty-state">No events captured yet.</p>
            ) : (
              events.map((event) => (
                <div key={event.id} className={`debug-event level-${event.level}`}>
                  <div className="debug-event-meta">
                    <span>{formatTimestamp(event.timestamp)}</span>
                    <span>{event.level.toUpperCase()}</span>
                    <span>{event.source}</span>
                  </div>
                  <p className="debug-event-message">{event.message}</p>
                  {event.detail && <pre>{formatDebugDetail(event.detail)}</pre>}
                </div>
              ))
            )}
          </div>
        </section>
        <section className="debug-section">
          <h4>Server logs</h4>
          {!token && <p className="helper-text">Sign in to retrieve server logs.</p>}
          {serverLogsError && <p className="error-banner">{serverLogsError}</p>}
          {serverLogs && (
            <p className="helper-text">
              Last updated {new Date(serverLogs.updated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
              {serverLogs.viewer ? ` · viewed as ${serverLogs.viewer}` : ""}
            </p>
          )}
          <pre className="server-log-block">
            {loading
              ? "Loading …"
              : (serverLogs?.lines ?? []).join("\n") || "No log output captured yet."}
          </pre>
        </section>
      </aside>
    )}
  </>
);

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

  const [serverUrl, setServerUrl] = useState(() => safeRead("restormer.serverUrl") ?? defaultServerUrl);
  const [serverUrlInput, setServerUrlInput] = useState(serverUrl);
  const [serverUrlError, setServerUrlError] = useState<string | null>(null);
  const [serverProbeMessage, setServerProbeMessage] = useState<string>("");
  const [probeBusy, setProbeBusy] = useState(false);

  const [token, setToken] = useState<string | null>(() => safeRead("restormer.token"));
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
  const [selectedMode, setSelectedMode] = useState<PipelineMode>("denoise");
  const [selectedPasses, setSelectedPasses] = useState<number>(1);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [uploadWarning, setUploadWarning] = useState<string | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);

  const [debugPanelOpen, setDebugPanelOpen] = useState(false);
  const [debugEvents, setDebugEvents] = useState<DebugEvent[]>(() => debugBus.snapshot());
  const [serverLogs, setServerLogs] = useState<DiagnosticsLogResponse | null>(null);
  const [serverLogsError, setServerLogsError] = useState<string | null>(null);
  const [serverLogsLoading, setServerLogsLoading] = useState(false);

  const apiClient = useMemo(() => createApiClient(serverUrl), [serverUrl]);
  const jobsQuery = useJobsQuery(apiClient, token, phase, serverUrl);

  const jobs = useMemo(() => {
    if (!jobsQuery.data) {
      return [] as JobResponse[];
    }
    if (!Array.isArray(jobsQuery.data)) {
      debug.error("jobs", "Received unexpected jobs payload", { payload: jobsQuery.data });
      return [] as JobResponse[];
    }
    return jobsQuery.data;
  }, [jobsQuery.data]);

  useEffect(() => safeWrite("restormer.serverUrl", serverUrl), [serverUrl]);
  useEffect(() => safeWrite("restormer.token", token), [token]);
  useEffect(() => debugBus.subscribe(setDebugEvents), []);

  useEffect(() => {
    if (phase !== "dashboard" || jobs.length === 0) {
      return;
    }
    if (selectedJobId === null) {
      setSelectedJobId(jobs[0]?.id ?? null);
      return;
    }
    if (!jobs.some((job) => job.id === selectedJobId)) {
      setSelectedJobId(jobs[0]?.id ?? null);
    }
  }, [jobs, phase, selectedJobId]);

  useEffect(() => {
    let cancelled = false;

    const initialise = async () => {
      debug.info("startup", "Initialising client state");
      setPhase("splash");
      setLoadingState({ message: "Restoring preferences…", progress: 0.22 });
      const storedServer = safeRead("restormer.serverUrl") ?? defaultServerUrl;
      if (cancelled) {
        return;
      }
      setServerUrl(storedServer);
      setServerUrlInput(storedServer);

      const client = createApiClient(storedServer);
      setLoadingState({ message: "Checking server availability…", progress: 0.45 });
      try {
        await Promise.race([
          client.health(),
          new Promise((_, reject) =>
            window.setTimeout(() => reject(new Error("Health check timeout")), HEALTH_CHECK_TIMEOUT)
          )
        ]);
        debug.info("startup", "Server health verified", { server: storedServer });
      } catch (error) {
        if (cancelled) {
          return;
        }
        debug.error("startup", "Failed during bootstrap", error);
        setServerUrlError("Could not reach the server. Please confirm the URL.");
        setPhase("configureServer");
        return;
      }

      if (cancelled) {
        return;
      }

      const storedToken = safeRead("restormer.token");
      if (storedToken) {
        setLoadingState({ message: "Verifying session…", progress: 0.65 });
        try {
          const me = await client.fetchProfile(storedToken);
          if (cancelled) {
            return;
          }
          setToken(storedToken);
          setProfile(me);
          debug.info("auth.session", "Restored existing session", { email: me.email });
          setLoadingState({ message: `Welcome back, ${me.full_name}`, progress: 0.92 });
          setPhase("dashboard");
          return;
        } catch (error) {
          debug.warn("auth.session", "Stored session invalid", error);
          safeWrite("restormer.token", null);
        }
      }

      if (cancelled) {
        return;
      }

      setLoadingState({ message: "Let’s connect you to the studio", progress: 0.88 });
      setPhase("onboard");
    };

    void initialise();

    return () => {
      cancelled = true;
    };
  }, []);

  const verifyWhitelistMutation = useMutation({
    mutationFn: async (email: string) => apiClient.verifyWhitelist(email),
    onSuccess: (response) => {
      setVerification(response);
      setOnboardingError(null);
      debug.info("auth.whitelist", "Whitelist confirmed", { email: newEmail, allowed: response.allowed });
    },
    onError: (error: unknown) => {
      const message = extractErrorMessage(error, "Unable to check whitelist");
      setOnboardingError(message);
      debug.error("auth.whitelist", "Whitelist check failed", { email: newEmail, message, error });
    }
  });

  const registerMutation = useMutation<TokenResponse, Error, { email: string; full_name: string; password: string }>({
    mutationFn: async (payload) => {
      await apiClient.registerUser(payload);
      return apiClient.loginWithPassword(payload.email, payload.password);
    }
  });

  const loginMutation = useMutation<TokenResponse, Error, { email: string; password: string }>({
    mutationFn: ({ email, password }) => apiClient.loginWithPassword(email, password)
  });

  const handleAuthenticated = useCallback(
    async (accessToken: string) => {
      debug.info("auth.session", "Establishing new session");
      setPhase("splash");
      setLoadingState({ message: "Securing your studio session…", progress: 0.72 });
      try {
        const me = await apiClient.fetchProfile(accessToken);
        setToken(accessToken);
        setProfile(me);
        setLoadingState({ message: `Hello ${me.full_name}`, progress: 0.98 });
        setPhase("dashboard");
        debug.info("auth.session", "Session established", { email: me.email });
      } catch (error) {
        debug.error("auth.session", "Failed to establish session", error);
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
      debug.info("upload", "Initialising upload mutation");
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
      debug.info("upload", "Upload succeeded");
      void jobsQuery.refetch();
      window.setTimeout(() => setUploadProgress(0), 700);
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : "Upload failed";
      setUploadWarning(message);
      setUploadProgress(0);
      debug.error("upload", "Upload failed", error);
    }
  });

  const handleSelectFiles = useCallback(async () => {
    if (uploadMutation.isPending || !token) {
      debug.warn("upload", "File selection blocked", { pending: uploadMutation.isPending, authenticated: Boolean(token) });
      return;
    }
    const files = await window.electronAPI.openFiles();
    if (!files || files.length === 0) {
      debug.warn("upload", "File picker closed without selection");
      return;
    }
    const trimmed = files.slice(0, 25);
    debug.info("upload", "File selection", { requested: files.length, accepted: trimmed.length });
    if (files.length > trimmed.length) {
      setUploadWarning("Only the first 25 images will be queued per batch.");
    } else {
      setUploadWarning(null);
    }
    const option = pipelineOptions.find((item) => item.value === selectedMode);
    const label = option?.label ?? selectedMode;
    setUploadMessage(
      `Uploading ${trimmed.length} image${trimmed.length === 1 ? "" : "s"} with ${label} · ${selectedPasses}x passes.`
    );
    const formData = new FormData();
    formData.append("mode", selectedMode);
    formData.append("passes", String(selectedPasses));
    trimmed.forEach((file, index) => {
      const blob = base64ToBlob(file.buffer);
      formData.append(`file_${index}`, blob, file.name);
    });
    await uploadMutation.mutateAsync(formData);
  }, [uploadMutation, token, selectedMode, selectedPasses]);

  const handleVerifyAccess = useCallback(async () => {
    setOnboardingError(null);
    if (!newEmail) {
      setOnboardingError("Enter the email you would like to register with.");
      return;
    }
    debug.info("auth.whitelist", "Checking whitelist", { email: newEmail });
    await verifyWhitelistMutation.mutateAsync(newEmail);
  }, [newEmail, verifyWhitelistMutation]);

  const handleRegister = useCallback(async () => {
    setOnboardingError(null);
    debug.info("auth.register", "Attempting registration", { email: newEmail });
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
      const message = extractErrorMessage(error, "Registration failed");
      setOnboardingError(message);
      debug.error("auth.register", "Registration failed", { email: newEmail, message, error });
    }
  }, [
    confirmPassword,
    handleAuthenticated,
    newEmail,
    newFullName,
    newPassword,
    registerMutation,
    verification?.allowed
  ]);

  const handleLogin = useCallback(async () => {
    setOnboardingError(null);
    debug.info("auth.login", "Attempting login", { email: loginEmail });
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
      const message = extractErrorMessage(error, "Sign-in failed");
      setOnboardingError(message);
      debug.error("auth.login", "Sign-in failed", { email: loginEmail, message, error });
    }
  }, [handleAuthenticated, loginEmail, loginMutation, loginPassword]);

  const handleLogout = useCallback(() => {
    debug.info("auth.logout", "Signing out user");
    setToken(null);
    setProfile(null);
    safeWrite("restormer.token", null);
    setPhase("onboard");
  }, []);

  const selectedJob = jobs.find((job) => job.id === selectedJobId) ?? null;

  const latestDebug = useMemo(() => {
    if (jobs.length === 0) {
      return [] as { job: JobResponse; line: string; index: number }[];
    }
    const tail = jobs.flatMap((job) => job.debug_lines.slice(-3).map((line, index) => ({ job, line, index })));
    return tail.slice(-15).reverse();
  }, [jobs]);

  const sortedDebugEvents = useMemo(() => [...debugEvents].reverse(), [debugEvents]);

  const handleServerProbe = useCallback(async () => {
    if (!serverUrlInput) {
      setServerUrlError("Enter a server URL before continuing.");
      return;
    }
    setProbeBusy(true);
    setServerUrlError(null);
    setServerProbeMessage("");
    const trimmed = serverUrlInput.trim().replace(/\/+$/, "");
    const client = createApiClient(trimmed);
    try {
      await Promise.race([
        client.health(),
        new Promise((_, reject) =>
          window.setTimeout(() => reject(new Error("Health check timeout")), HEALTH_CHECK_TIMEOUT)
        )
      ]);
      setServerUrl(trimmed);
      setServerProbeMessage("Server verified. Proceed with onboarding.");
      setPhase((current) => (current === "configureServer" ? "onboard" : current));
      debug.info("server.url", "Server URL updated", { serverUrl: trimmed });
    } catch (error) {
      const message = extractErrorMessage(error, "Could not reach the server. Confirm the address.");
      setServerUrlError(message);
      debug.error("server.url", "Server probe failed", { serverUrl: trimmed, message, error });
    } finally {
      setProbeBusy(false);
    }
  }, [serverUrlInput]);

  const handleFetchServerLogs = useCallback(async () => {
    if (!token) {
      return;
    }
    setServerLogsError(null);
    setServerLogsLoading(true);
    try {
      const logs = await apiClient.fetchDiagnosticsLogs(token);
      setServerLogs(logs);
      debug.info("diagnostics.logs", "Fetched server logs", { lines: logs.lines.length });
    } catch (error) {
      const message = extractErrorMessage(error, "Unable to fetch server logs");
      setServerLogsError(message);
      debug.error("diagnostics.logs", "Failed to fetch server logs", { message, error });
    } finally {
      setServerLogsLoading(false);
    }
  }, [apiClient, token]);

  const handleDownload = useCallback(
    (jobId: number) => {
      if (!token) {
        return;
      }
      void apiClient.downloadProcessedImage(token, jobId);
    },
    [apiClient, token]
  );

  const jobsQueryState = {
    ...jobsQuery,
    data: jobs
  };

  const uploadState: UploadPanelProps = {
    selectedMode,
    onModeChange: setSelectedMode,
    selectedPasses,
    onPassChange: setSelectedPasses,
    onSelectFiles: handleSelectFiles,
    uploadProgress,
    uploadMessage,
    uploadWarning,
    uploadDisabled: uploadMutation.isPending
  };

  return (
    <div className="app-root">
      <div className="app-gradient" />
      {phase === "splash" ? (
        <SplashScreen {...loadingState} />
      ) : (
        <div className="app-shell">
          {(phase === "configureServer" || phase === "onboard") && (
            <ServerConfigurator
              serverUrl={serverUrl}
              inputValue={serverUrlInput}
              error={serverUrlError}
              message={serverProbeMessage}
              busy={probeBusy}
              onInput={setServerUrlInput}
              onReset={() => setServerUrlInput(serverUrl)}
              onSubmit={handleServerProbe}
            />
          )}
          {phase === "onboard" && (
            <OnboardingPanel
              mode={onboardingMode}
              verification={verification}
              onboardingError={onboardingError}
              newEmail={newEmail}
              newFullName={newFullName}
              newPassword={newPassword}
              confirmPassword={confirmPassword}
              loginEmail={loginEmail}
              loginPassword={loginPassword}
              onModeChange={(value) => {
                setOnboardingMode(value);
                setOnboardingError(null);
              }}
              onEmailChange={setNewEmail}
              onFullNameChange={setNewFullName}
              onPasswordChange={setNewPassword}
              onConfirmPasswordChange={setConfirmPassword}
              onLoginEmailChange={setLoginEmail}
              onLoginPasswordChange={setLoginPassword}
              onVerifyAccess={handleVerifyAccess}
              onRegister={handleRegister}
              onLogin={handleLogin}
              verifying={verifyWhitelistMutation.isPending}
              registering={registerMutation.isPending}
              loggingIn={loginMutation.isPending}
            />
          )}
          {phase === "dashboard" && profile && (
            <Dashboard
              profile={profile}
              onLogout={handleLogout}
              uploadState={uploadState}
              jobs={jobs}
              selectedJob={selectedJob}
              onSelectJob={setSelectedJobId}
              jobsQueryState={jobsQueryState}
              latestDebug={latestDebug}
              token={token}
              onDownload={handleDownload}
            />
          )}
        </div>
      )}
      <DebugPanelOverlay
        open={debugPanelOpen}
        events={sortedDebugEvents}
        onToggle={() => setDebugPanelOpen((value) => !value)}
        onClear={() => debugBus.clear()}
        onFetchLogs={handleFetchServerLogs}
        loading={serverLogsLoading}
        token={token}
        serverLogs={serverLogs}
        serverLogsError={serverLogsError}
      />
    </div>
  );
};

export default App;

