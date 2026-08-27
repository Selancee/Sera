import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import RuntimeErrorBoundary from "./components/RuntimeErrorBoundary.jsx";
import { StartupScreen } from "./desktop/startupScreen";
import { I18nProvider } from "./i18n";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <RuntimeErrorBoundary resetKey="root" scope="root" title="Sera could not render">
      <I18nProvider>
        <StartupScreen>
          <App />
        </StartupScreen>
      </I18nProvider>
    </RuntimeErrorBoundary>
  </React.StrictMode>
);
