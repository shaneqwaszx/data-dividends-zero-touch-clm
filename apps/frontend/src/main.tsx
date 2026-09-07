import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { AuthProvider, useAuth } from "./auth";
import LoginPage from "./pages/LoginPage";
import "./styles.css";
import "./design-system.css";

function AuthenticatedApplication() {
  const { status, session, logout } = useAuth();
  if (status === "loading") {
    return <main className="ds-root auth-page"><p className="text-muted">Restoring session…</p></main>;
  }
  if (status === "anonymous" || !session) return <LoginPage />;
  return <App actor={session.profile} onLogout={() => void logout()} />;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <AuthenticatedApplication />
    </AuthProvider>
  </StrictMode>,
);
