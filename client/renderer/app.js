const $ = (id) => document.getElementById(id);
const profiles = {
  balanced: "Safer default: observe after actions, prefer accessibility tree, request screenshots only when useful.",
  fast: "Warms the local model and trims waits while still verifying actions after UI changes.",
  ultra_low: "Most responsive: prefetches tree + screenshot thumbnails and can optimistically run low-risk clicks; higher battery/privacy trade-off."
};
const commands = {
  messages: { action: "open_app", params: { name: "Messages" }, reason: "favorite shortcut", risk: "low", requires_approval: false },
  tree: { action: "get_tree", params: {}, reason: "show current screen summary", risk: "low", requires_approval: false },
  stop: { action: "stop", params: {}, reason: "visible kill switch", risk: "low", requires_approval: false },
  approve: { action: "tap_element", params: { label: "Approve" }, reason: "approve visible pending action", risk: "medium", requires_approval: true }
};

const state = {
  get baseUrl() { return $("gatewayUrl").value.replace(/\/$/, ""); },
  get token() { return $("token").value; }
};

const setStatus = (text) => { $("status").textContent = text; };
const setOutput = (value) => { $("output").textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2); };
const save = () => {
  localStorage.setItem("gatewayUrl", $("gatewayUrl").value);
  localStorage.setItem("gatewayToken", $("token").value);
  setStatus("Settings saved locally on this Mac.");
};
const gatewayFetch = async (path, options = {}) => {
  const response = await fetch(`${state.baseUrl}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${state.token}`, ...(options.headers || {}) }
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || `Gateway request failed with ${response.status}`);
  return body;
};
const sendCommand = async (command) => {
  try {
    save();
    const result = await gatewayFetch("/v1/commands", { method: "POST", body: JSON.stringify(command) });
    setOutput(result);
    setStatus(result.status === "needs_approval" ? "Awaiting approval" : "Command sent");
  } catch (error) { setStatus(error.message); }
};

$("gatewayUrl").value = localStorage.getItem("gatewayUrl") || $("gatewayUrl").value;
$("token").value = localStorage.getItem("gatewayToken") || "";
$("command").value = JSON.stringify(commands.tree, null, 2);
$("profileDescription").textContent = profiles[$("profile").value];
$("profile").addEventListener("change", () => { $("profileDescription").textContent = profiles[$("profile").value]; });
$("silence").addEventListener("input", () => { $("silenceLabel").textContent = $("silence").value; });
$("save").addEventListener("click", save);
$("test").addEventListener("click", async () => {
  try {
    save();
    const [health, status] = await Promise.all([gatewayFetch("/health"), gatewayFetch("/v1/status")]);
    setOutput(status);
    setStatus(`Connected: ${health.status}, bridge ${status.bridge}`);
  } catch (error) { setStatus(error.message); }
});
document.querySelectorAll("[data-command]").forEach((button) => button.addEventListener("click", () => sendCommand(commands[button.dataset.command])));
$("send").addEventListener("click", () => {
  try { sendCommand(JSON.parse($("command").value)); } catch (error) { setStatus(`Invalid command JSON: ${error.message}`); }
});
$("voice").addEventListener("click", async () => {
  try {
    save();
    const result = await gatewayFetch("/v1/interjections", {
      method: "POST",
      body: JSON.stringify({ question: $("question").value, reason: "agent needs to ask or confirm something", urgency: "normal", max_listen_seconds: 45, silence_ms: Number($("silence").value), transcript_mode: $("voiceBreak").checked ? "controller_only" : "off" })
    });
    setOutput(result);
    setStatus("Voice portal requested: listen for natural break, interject, then shut off mic.");
  } catch (error) { setStatus(error.message); }
});
