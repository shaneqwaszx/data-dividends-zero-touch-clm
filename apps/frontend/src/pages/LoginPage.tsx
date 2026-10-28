import { useState, type FormEvent } from "react";

import { useAuth } from "../auth";

export default function LoginPage() {
  const { error, notice, login } = useAuth();
  const [userId, setUserId] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      await login(userId.trim(), password);
      setPassword("");
    } catch {
      setPassword("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="ds-root auth-page">
      <section className="card auth-card" aria-labelledby="sign-in-heading">
        <p className="card-kicker">Autoboard · Local POC</p>
        <h1 id="sign-in-heading">Sign in</h1>
        <p className="text-muted">Use a configured synthetic operator profile.</p>
        {notice && <div className="ds-banner" role="status" data-testid="session-end-notice">{notice}</div>}
        {error && <div className="ds-banner ds-banner-warn" role="alert">{error}</div>}
        <form onSubmit={(event) => void handleSubmit(event)}>
          <label htmlFor="user-id">User ID</label>
          <input
            id="user-id"
            className="input"
            autoComplete="username"
            value={userId}
            onChange={(event) => setUserId(event.target.value)}
            required
          />
          <label htmlFor="password">Password</label>
          <input
            id="password"
            className="input"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
