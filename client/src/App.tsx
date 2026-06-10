import React, { useMemo, useState } from "react";
import { createInterjection, getHealth, getStatus, sendCommand, type CommandRequest } from "./api";

type LatencyProfile = "balanced" | "fast" | "ultra_low";

const profileDescriptions: Record<LatencyProfile, string> = {
  balanced: "Safer default: observe after actions, prefer accessibility tree, request screenshots only when useful.",
  fast: "Warms the local model and trims waits while still verifying actions after UI changes.",
  ultra_low: "Most responsive: prefetches tree + screenshot thumbnails and can optimistically run low-risk clicks; higher battery/privacy trade-off."
};

const defaultCommand: CommandRequest = {
  action: "get_tree",
  params: {},
  reason: "show current screen summary",
  risk: "low",
  requires_approval: false
};

const App: React.FC = () => {
  const [gatewayUrl, setGatewayUrl] = useState(localStorage.getItem("gatewayUrl") ?? "http://127.0.0.1:8788");
  const [token, setToken] = useState(localStorage.getItem("gatewayToken") ?? "");
  const [status, setStatus] = useState("Not connected");
  const [result, setResult] = useState("");
  const [latencyProfile, setLatencyProfile] = useState<LatencyProfile>("balanced");
  const [autoScreenshot, setAutoScreenshot] = useState(false);
  const [prefetchTree, setPrefetchTree] = useState(true);
  const [voiceBreak, setVoiceBreak] = useState(true);
  const [silenceMs, setSilenceMs] = useState(900);
  const [question, setQuestion] = useState("I need your approval before sending this message.");
  const [command, setCommand] = useState<CommandRequest>(defaultCommand);

  const tradeoffs = useMemo(
    () => [
      { label: "Prefetch accessibility tree", value: prefetchTree, detail: "Faster first click decisions with a small local RPC cost." },
      { label: "Auto screenshot thumbnail", value: autoScreenshot, detail: "Avoids an extra model round trip for visual tasks; costs battery and captures screen pixels locally." },
      { label: "Voice natural-break portal", value: voiceBreak, detail: "iPhone mic opens only while waiting for a pause, then closes after interjection." }
    ],
    [autoScreenshot, prefetchTree, voiceBreak]
  );

  const persistSettings = () => {
    localStorage.setItem("gatewayUrl", gatewayUrl);
    localStorage.setItem("gatewayToken", token);
    setStatus("Settings saved locally on this Mac.");
  };

  const testConnection = async () => {
    try {
      persistSettings();
      const [health, gatewayStatus] = await Promise.all([getHealth(gatewayUrl, token), getStatus(gatewayUrl, token)]);
      setStatus(`Connected: ${health.status}, bridge ${gatewayStatus.bridge}`);
      setResult(JSON.stringify(gatewayStatus, null, 2));
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Connection failed");
    }
  };

  const runCommand = async (nextCommand = command) => {
    try {
      const response = await sendCommand(gatewayUrl, token, nextCommand);
      setResult(JSON.stringify(response, null, 2));
      setStatus(response.status === "needs_approval" ? "Awaiting approval" : "Command sent");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Command failed");
    }
  };

  const openVoicePortal = async () => {
    try {
      const response = await createInterjection(gatewayUrl, token, {
        question,
        reason: "agent needs to ask or confirm something",
        urgency: "normal",
        max_listen_seconds: 45,
        silence_ms: silenceMs,
        transcript_mode: voiceBreak ? "controller_only" : "off"
      });
      setResult(JSON.stringify(response, null, 2));
      setStatus("Voice portal requested: listen for natural break, interject, then shut off mic.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Voice portal request failed");
    }
  };

  return (
    <main className="shell">
      <section className="hero card glow">
        <p className="eyebrow">PhoneAgent host controller</p>
        <h1>Secure tailnet control, faster clicks, natural-break questions.</h1>
        <p>
          Configure the Mac gateway, choose speed/privacy trade-offs, and let the iPhone controller use its microphone briefly
          when the agent needs to interject at a natural pause.
        </p>
        <div className="status-pill">{status}</div>
      </section>

      <section className="grid two">
        <div className="card">
          <h2>Gateway</h2>
          <label>Gateway URL</label>
          <input value={gatewayUrl} onChange={(event) => setGatewayUrl(event.target.value)} />
          <label>Bearer token</label>
          <input type="password" value={token} onChange={(event) => setToken(event.target.value)} />
          <div className="row">
            <button onClick={testConnection}>Test connection</button>
            <button className="secondary" onClick={persistSettings}>Save locally</button>
          </div>
          <p className="hint">Use Tailscale Serve for remote access. Do not expose the raw JSON-RPC bridge or use Funnel.</p>
        </div>

        <div className="card">
          <h2>Latency mode</h2>
          <select value={latencyProfile} onChange={(event) => setLatencyProfile(event.target.value as LatencyProfile)}>
            <option value="balanced">Balanced</option>
            <option value="fast">Fast</option>
            <option value="ultra_low">Ultra-low latency</option>
          </select>
          <p className="hint">{profileDescriptions[latencyProfile]}</p>
          <label className="check"><input type="checkbox" checked={prefetchTree} onChange={(event) => setPrefetchTree(event.target.checked)} /> Prefetch tree</label>
          <label className="check"><input type="checkbox" checked={autoScreenshot} onChange={(event) => setAutoScreenshot(event.target.checked)} /> Auto-send screenshot thumbnail locally</label>
          <label className="check"><input type="checkbox" checked={voiceBreak} onChange={(event) => setVoiceBreak(event.target.checked)} /> Enable voice natural-break portal</label>
          <div className="tradeoffs">
            {tradeoffs.map((item) => (
              <div key={item.label} className={item.value ? "tradeoff on" : "tradeoff"}>
                <strong>{item.label}</strong>
                <span>{item.detail}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid two">
        <div className="card">
          <h2>Quick actions</h2>
          <div className="row wrap">
            {[
              { label: "Open Messages", command: { action: "open_app", params: { name: "Messages" }, reason: "favorite shortcut", risk: "low", requires_approval: false } },
              { label: "Screen summary", command: defaultCommand },
              { label: "Stop", command: { action: "stop", params: {}, reason: "visible kill switch", risk: "low", requires_approval: false } },
              { label: "Approve pending", command: { action: "tap_element", params: { label: "Approve" }, reason: "approve visible pending action", risk: "medium", requires_approval: true } }
            ].map((item) => (
              <button key={item.label} className="secondary" onClick={() => runCommand(item.command as CommandRequest)}>{item.label}</button>
            ))}
          </div>
          <label>Raw command JSON</label>
          <textarea value={JSON.stringify(command, null, 2)} onChange={(event) => setCommand(JSON.parse(event.target.value))} />
          <button onClick={() => runCommand()}>Send command</button>
        </div>

        <div className="card">
          <h2>Natural-break voice portal</h2>
          <p className="hint">When the agent needs to ask a question, the iPhone controller can briefly listen for speech activity, wait for silence, interject, then close the microphone path to save battery.</p>
          <label>Question to interject</label>
          <textarea value={question} onChange={(event) => setQuestion(event.target.value)} />
          <label>Silence threshold: {silenceMs} ms</label>
          <input type="range" min="400" max="1800" value={silenceMs} onChange={(event) => setSilenceMs(Number(event.target.value))} />
          <button onClick={openVoicePortal}>Open voice portal request</button>
        </div>
      </section>

      <section className="card output">
        <h2>Gateway response</h2>
        <pre>{result || "No response yet."}</pre>
      </section>
    </main>
  );
};

export default App;
