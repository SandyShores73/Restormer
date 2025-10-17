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
        <div className="fatal-error">
          <div className="fatal-card">
            <h1>Renderer crash detected</h1>
            <p>{error.message}</p>
            {info?.componentStack && <pre>{info.componentStack}</pre>}
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
