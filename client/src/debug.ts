import type { AxiosError } from "axios";

export type DebugLevel = "info" | "warn" | "error";

export interface DebugEvent {
  id: string;
  timestamp: number;
  level: DebugLevel;
  source: string;
  message: string;
  detail?: unknown;
}

export type DebugListener = (events: DebugEvent[]) => void;

const serialiseDetail = (detail: unknown) => {
  if (detail instanceof Error) {
    return {
      name: detail.name,
      message: detail.message,
      stack: detail.stack
    };
  }
  const maybeAxios = detail as AxiosError | undefined;
  if (maybeAxios && typeof maybeAxios === "object" && "isAxiosError" in maybeAxios) {
    return {
      name: maybeAxios.name,
      message: maybeAxios.message,
      status: maybeAxios.response?.status,
      data: maybeAxios.response?.data
    };
  }
  return detail;
};

class DebugBus {
  private events: DebugEvent[] = [];

  private listeners = new Set<DebugListener>();

  constructor(private capacity = 200) {}

  record(level: DebugLevel, source: string, message: string, detail?: unknown) {
    const event: DebugEvent = {
      id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
      timestamp: Date.now(),
      level,
      source,
      message,
      detail: serialiseDetail(detail)
    };
    const next = [...this.events, event];
    if (next.length > this.capacity) {
      next.splice(0, next.length - this.capacity);
    }
    this.events = next;
    this.notify();
    this.logToConsole(event);
  }

  subscribe(listener: DebugListener): () => void {
    this.listeners.add(listener);
    listener(this.snapshot());
    return () => {
      this.listeners.delete(listener);
    };
  }

  snapshot(): DebugEvent[] {
    return [...this.events];
  }

  clear(): void {
    this.events = [];
    this.notify();
  }

  private notify(): void {
    const snapshot = this.snapshot();
    this.listeners.forEach((listener) => listener(snapshot));
  }

  private logToConsole(event: DebugEvent): void {
    const prefix = `[${event.source}] ${event.message}`;
    if (event.level === "info") {
      console.info(prefix, event.detail ?? "");
    } else if (event.level === "warn") {
      console.warn(prefix, event.detail ?? "");
    } else {
      console.error(prefix, event.detail ?? "");
    }
  }
}

export const debugBus = new DebugBus();

export const debug = {
  info(source: string, message: string, detail?: unknown) {
    debugBus.record("info", source, message, detail);
  },
  warn(source: string, message: string, detail?: unknown) {
    debugBus.record("warn", source, message, detail);
  },
  error(source: string, message: string, detail?: unknown) {
    debugBus.record("error", source, message, detail);
  }
};

if (typeof window !== "undefined") {
  (window as typeof window & { __LUMA_DEBUG__?: DebugBus }).__LUMA_DEBUG__ = debugBus;
}
