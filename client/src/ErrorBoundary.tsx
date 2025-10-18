import React from "react";
import { debug } from "./debug";

interface ErrorBoundaryState {
  error: Error | null;
  info: React.ErrorInfo | null;
}

export class ErrorBoundary extends React.Component<React.PropsWithChildren<Record<string, never>>, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null, info: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error, info: null };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    this.setState({ error, info });
    debug.error("ui.errorBoundary", error.message, {
      stack: error.stack,
      componentStack: info.componentStack
    });
  }

  private handleReload = () => {
    this.setState({ error: null, info: null });
    window.location.reload();
  };

  render(): React.ReactNode {
    const { error, info } = this.state;
    if (error) {
      return (
        <div
          className="fatal-error"
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(5, 6, 10, 0.96)",
            zIndex: 60,
            display: "grid",
            placeItems: "center",
            padding: "2rem"
          }}
        >
          <div
            className="fatal-card"
            style={{
              width: "min(540px, 94vw)",
              background: "rgba(12, 15, 28, 0.9)",
              border: "1px solid rgba(255, 122, 135, 0.45)",
              borderRadius: "30px",
              boxShadow: "0 32px 90px rgba(6, 10, 28, 0.65)",
              padding: "2.6rem",
              display: "flex",
              flexDirection: "column",
              gap: "1.2rem",
              alignItems: "center",
              textAlign: "center"
            }}
          >
            <h1 style={{ margin: 0, fontSize: "1.6rem" }}>Renderer crash detected</h1>
            <p style={{ margin: 0, color: "rgba(255, 214, 224, 0.9)" }}>{error.message}</p>
            {info?.componentStack && (
              <pre
                style={{
                  width: "100%",
                  maxHeight: "220px",
                  overflowY: "auto",
                  padding: "1rem",
                  borderRadius: "16px",
                  background: "rgba(8, 10, 18, 0.9)",
                  border: "1px solid rgba(255, 122, 135, 0.35)",
                  fontFamily: '"SFMono-Regular", Menlo, Consolas, monospace',
                  fontSize: "0.78rem",
                  textAlign: "left",
                  color: "rgba(255, 214, 224, 0.9)"
                }}
              >
                {info.componentStack}
              </pre>
            )}
            <button type="button" onClick={this.handleReload}>
              Reload Luma Studio
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
