export type GatewayStatus = {
  status: string;
  bridge: string;
  latency_options?: Record<string, unknown>;
  latency_descriptions?: Record<string, string>;
  voice_break_mode?: boolean;
};

export type CommandRequest = {
  action: string;
  params: Record<string, unknown>;
  reason: string;
  risk: "low" | "medium" | "high";
  requires_approval: boolean;
};

export type InterjectionRequest = {
  question: string;
  reason: string;
  urgency: "low" | "normal" | "urgent";
  max_listen_seconds: number;
  silence_ms: number;
  transcript_mode: "controller_only" | "local_only" | "off";
};

const gatewayFetch = async <T,>(baseUrl: string, token: string, path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(`${baseUrl.replace(/\/$/, "")}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {})
    }
  });
  const text = await response.text();
  const body = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(body.error ?? `Gateway request failed with ${response.status}`);
  }
  return body as T;
};

export const getHealth = (baseUrl: string, token: string) =>
  gatewayFetch<{ status: string; uptime_s: number }>(baseUrl, token, "/health");

export const getStatus = (baseUrl: string, token: string) =>
  gatewayFetch<GatewayStatus>(baseUrl, token, "/v1/status");

export const sendCommand = (baseUrl: string, token: string, command: CommandRequest) =>
  gatewayFetch<Record<string, unknown>>(baseUrl, token, "/v1/commands", {
    method: "POST",
    body: JSON.stringify(command)
  });

export const createInterjection = (baseUrl: string, token: string, request: InterjectionRequest) =>
  gatewayFetch<Record<string, unknown>>(baseUrl, token, "/v1/interjections", {
    method: "POST",
    body: JSON.stringify(request)
  });
