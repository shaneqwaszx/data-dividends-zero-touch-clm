import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";

import App from "./App";
import { AuthProvider, useAuth } from "./auth";
import LoginPage from "./pages/LoginPage";
import "./styles.css";
import "./design-system.css";

export function AuthenticatedApplication() {
  const { status, session, logout, changeOwnPassword } = useAuth();
  if (status === "loading") {
    return <main className="ds-root auth-page"><p className="text-muted">Restoring session…</p></main>;
  }
  if (status === "anonymous" || !session) return <LoginPage />;
  return <App
    key={session.profile.user_id}
    actor={session.profile}
    onLogout={() => void logout()}
    onChangeOwnPassword={changeOwnPassword}
  />;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <AuthenticatedApplication />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
