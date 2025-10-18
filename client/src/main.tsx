import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import { ErrorBoundary } from "./ErrorBoundary";
import "./styles.css";

const client = new QueryClient();
const container = document.getElementById("root");

if (!container) {
  throw new Error("Failed to locate root element");
}

const root = ReactDOM.createRoot(container);

root.render(
  <ErrorBoundary>
    <React.StrictMode>
      <QueryClientProvider client={client}>
        <App />
      </QueryClientProvider>
    </React.StrictMode>
  </ErrorBoundary>
);
