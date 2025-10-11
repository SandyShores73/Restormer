const STATUS_COLORS = {
  queued: "#8aa4ff",
  processing: "#ffc86b",
  completed: "#63f8c8",
  failed: "#ff6b7a"
};

const STAGE_LABELS = {
  queued: "Queued",
  initialising: "Initialising",
  preparing: "Preparing input",
  loading_models: "Loading models",
  denoise: "Restormer denoise",
  enhance: "Real-ESRGAN enhance",
  refocus: "NAFNet refocus",
  saving: "Saving output",
  completed: "Completed",
  failed: "Failed"
};

const connectionStatus = document.querySelector("#connection-status");
const environmentGrid = document.querySelector("#environment-grid");
const totalJobs = document.querySelector("#total-jobs");
const statusList = document.querySelector("#status-list");
const averageProgressFill = document.querySelector("#average-progress");
const recentJobsBody = document.querySelector("#recent-jobs");
const refreshButton = document.querySelector("#refresh-button");
const dashboardForm = document.querySelector("#dashboard-form");
const dashboardTokenInput = document.querySelector("#dashboard-token");

let dashboardToken = null;
let refreshInterval = null;

const updateConnectionStatus = (text, isError = false) => {
  connectionStatus.textContent = text;
  connectionStatus.classList.toggle("status-chip--error", isError);
};

const renderEnvironment = (environment) => {
  environmentGrid.innerHTML = "";
  const entries = [
    ["Available Providers", environment.available_providers.join(", ") || "Unknown"],
    ["Loaded Sessions", environment.loaded_sessions.join(", ") || "None"],
    ["Cached Models", environment.cached_models.join(", ") || "Downloading"],
    ["Models Directory", environment.models_directory]
  ];

  entries.forEach(([label, value]) => {
    const item = document.createElement("div");
    item.className = "environment-item";
    const labelEl = document.createElement("span");
    labelEl.textContent = label;
    const valueEl = document.createElement("strong");
    valueEl.textContent = value;
    item.append(labelEl, valueEl);
    environmentGrid.append(item);
  });
};

const renderStatusList = (counts) => {
  statusList.innerHTML = "";
  Object.entries(counts).forEach(([status, count]) => {
    const li = document.createElement("li");
    const pill = document.createElement("span");
    pill.className = "status-pill";
    pill.style.background = `${STATUS_COLORS[status] || "#5b8cff"}22`;
    pill.style.color = STATUS_COLORS[status] || "#bcd3ff";
    pill.innerHTML = `<span style="display:inline-block;width:0.6rem;height:0.6rem;border-radius:50%;background:${
      STATUS_COLORS[status] || "#5b8cff"
    };box-shadow:0 0 10px ${(STATUS_COLORS[status] || "#5b8cff") + "88"};"></span>${status}`;

    const total = document.createElement("strong");
    total.textContent = count;
    li.append(pill, total);
    statusList.append(li);
  });
};

const renderRecentJobs = (jobs) => {
  recentJobsBody.innerHTML = "";
  if (!jobs.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 7;
    cell.textContent = "No jobs submitted yet.";
    row.append(cell);
    recentJobsBody.append(row);
    return;
  }

  jobs.forEach((job) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>#${job.id}</td>
      <td>${STAGE_LABELS[job.stage] || job.stage}</td>
      <td>${job.status}</td>
      <td class="progress-cell">
        <div class="progress-bar">
          <div class="progress-bar__fill" style="width: ${Math.round(job.progress * 100)}%;"></div>
        </div>
      </td>
      <td>${new Date(job.updated_at).toLocaleString()}</td>
      <td>${job.filename || ""}</td>
      <td>${job.last_debug || "—"}</td>
    `;
    recentJobsBody.append(row);
  });
};

const fetchSummary = async () => {
  const headers = {};
  if (dashboardToken) {
    headers["X-Dashboard-Token"] = dashboardToken;
  }

  const response = await fetch("../diagnostics/summary", { headers });
  if (!response.ok) {
    throw new Error(`Dashboard request failed (${response.status})`);
  }
  return response.json();
};

const refreshData = async () => {
  try {
    updateConnectionStatus("Updating…");
    const summary = await fetchSummary();
    updateConnectionStatus("Live");
    totalJobs.textContent = summary.total_jobs;
    averageProgressFill.style.width = `${Math.round(summary.average_progress * 100)}%`;
    renderEnvironment(summary.environment);
    renderStatusList(summary.status_counts || {});
    renderRecentJobs(summary.recent_jobs || []);
  } catch (error) {
    console.error(error);
    updateConnectionStatus(error.message || "Offline", true);
  }
};

const scheduleRefresh = () => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
  refreshInterval = setInterval(refreshData, 5000);
};

refreshButton.addEventListener("click", () => {
  refreshData();
});

dashboardForm.addEventListener("submit", (event) => {
  event.preventDefault();
  dashboardToken = dashboardTokenInput.value.trim() || null;
  refreshData();
});

refreshData();
scheduleRefresh();
