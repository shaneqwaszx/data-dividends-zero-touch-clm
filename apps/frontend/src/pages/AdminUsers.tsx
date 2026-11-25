import { useEffect, useState, type FormEvent } from "react";

import {
  ApiError,
  createAdminProfile,
  disableAdminProfileSignIn,
  fetchAdminProfiles,
  fetchTeamOptions,
  resetAdminProfilePassword,
  updateAdminProfile,
} from "../api";
import { roleLabel } from "../roleLabels";
import type { AdminProfile, AuthenticatedTeam, Role, TeamId } from "../types";

type ChangeOwnPassword = (currentPassword: string, newPassword: string) => Promise<void>;

export default function AdminUsers({
  onChangeOwnPassword,
}: { onChangeOwnPassword?: ChangeOwnPassword }) {
  const [profiles, setProfiles] = useState<AdminProfile[]>([]);
  const [teams, setTeams] = useState<AuthenticatedTeam[]>([]);
  const [userId, setUserId] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState<Role>("CLIENT_ONBOARDER");
  const [teamId, setTeamId] = useState<TeamId | "">("");
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [error, setError] = useState<string | null>(null);
  // D-140: one reset form at a time; the page is already IDENTITY_ADMIN-gated and the
  // backend decides (HR accounts stay owner-managed, so their rows offer no reset).
  const [resetTarget, setResetTarget] = useState<AdminProfile | null>(null);
  const [resetPassword, setResetPassword] = useState("");
  const [resetConfirmation, setResetConfirmation] = useState("");
  const [resetNotice, setResetNotice] = useState<string | null>(null);
  const [credentialPending, setCredentialPending] = useState(false);
  const needsTeam = role === "CLIENT_ONBOARDER" || role === "RELATIONSHIP_MANAGER";

  useEffect(() => {
    void Promise.all([fetchAdminProfiles(), fetchTeamOptions()])
      .then(([nextProfiles, nextTeams]) => { setProfiles(nextProfiles); setTeams(nextTeams); })
      .catch((reason) => setError(reason instanceof ApiError ? reason.message : "User administration is unavailable."));
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    if (password !== passwordConfirmation) {
      setPassword("");
      setPasswordConfirmation("");
      setError("Password confirmation does not match.");
      return;
    }
    try {
      const created = await createAdminProfile({ user_id: userId, display_name: displayName, role, team_id: needsTeam ? teamId || null : null, password });
      setProfiles((current) => [...current, created]);
      setUserId(""); setDisplayName(""); setPassword(""); setPasswordConfirmation(""); setTeamId(""); setError(null);
    } catch (reason) {
      setPassword("");
      setPasswordConfirmation("");
      setError(reason instanceof ApiError ? reason.message : "User creation failed.");
    }
  }

  async function edit(profile: AdminProfile) {
    const nextName = globalThis.prompt("User display name", profile.display_name)?.trim();
    if (!nextName) return;
    const nextRole = globalThis.prompt(
      "Role: CLIENT_ONBOARDER, RELATIONSHIP_MANAGER, DIRECTOR, HR, or SUPPORT",
      profile.role,
    )?.trim() as Role | undefined;
    if (!nextRole || !["CLIENT_ONBOARDER", "RELATIONSHIP_MANAGER", "DIRECTOR", "HR", "SUPPORT"].includes(nextRole)) {
      setError("Select a valid role.");
      return;
    }
    const teamRequired = nextRole === "CLIENT_ONBOARDER" || nextRole === "RELATIONSHIP_MANAGER";
    const nextTeam = teamRequired
      ? globalThis.prompt("Canonical team ID", profile.team_id ?? teams[0]?.team_id ?? "")?.trim()
      : null;
    if (teamRequired && (!nextTeam || !teams.some((team) => team.team_id === nextTeam))) {
      setError("Select an existing active team.");
      return;
    }
    try {
      const changed = await updateAdminProfile(profile.user_id, {
        expected_version: profile.version,
        display_name: nextName,
        role: nextRole,
        team_id: teamRequired ? nextTeam as TeamId : null,
      });
      setProfiles((current) => current.map((item) => item.user_id === changed.user_id ? changed : item));
      setError(null);
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 409) {
        setProfiles(await fetchAdminProfiles());
      }
      setError(reason instanceof ApiError ? reason.message : "User update failed.");
    }
  }

  function openReset(profile: AdminProfile) {
    setResetTarget(profile);
    setResetPassword("");
    setResetConfirmation("");
    setResetNotice(null);
    setError(null);
  }

  function closeReset() {
    setResetTarget(null);
    setResetPassword("");
    setResetConfirmation("");
  }

  async function reset(event: FormEvent) {
    event.preventDefault();
    if (!resetTarget || credentialPending) return;
    const target = resetTarget;
    const nextPassword = resetPassword;
    const matches = nextPassword === resetConfirmation;
    setResetPassword("");
    setResetConfirmation("");
    if (!matches) {
      setError("Password confirmation does not match.");
      return;
    }
    setCredentialPending(true);
    setError(null);
    try {
      const changed = await resetAdminProfilePassword(target.user_id, { expected_version: target.version, new_password: nextPassword });
      setProfiles((current) => current.map((item) => item.user_id === changed.user_id ? changed : item));
      setResetTarget(null);
      setError(null);
      setResetNotice(`Password reset for ${changed.user_id}. Their existing sessions were signed out.`);
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 409) {
        const refreshed = await fetchAdminProfiles().catch(() => null);
        if (refreshed) {
          setProfiles(refreshed);
          setResetTarget(refreshed.find((item) => item.user_id === target.user_id && item.role !== "HR") ?? null);
        }
      }
      setResetNotice(null);
      setError(reason instanceof ApiError ? reason.message : "Password reset failed.");
    } finally {
      setCredentialPending(false);
    }
  }

  async function disableSignIn(profile: AdminProfile) {
    if (credentialPending || !globalThis.confirm(
      `Disable sign-in for ${profile.user_id}? This signs them out. Reset their password to restore access.`,
    )) return;
    closeReset();
    setResetNotice(null);
    setError(null);
    setCredentialPending(true);
    try {
      const changed = await disableAdminProfileSignIn(profile.user_id, profile.version);
      setProfiles((current) => current.map((item) => item.user_id === changed.user_id ? changed : item));
      setResetNotice(`Sign-in disabled for ${changed.user_id}.`);
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 409) {
        const refreshed = await fetchAdminProfiles().catch(() => null);
        if (refreshed) setProfiles(refreshed);
      }
      setError(reason instanceof ApiError ? reason.message : "Could not disable sign-in.");
    } finally {
      setCredentialPending(false);
    }
  }

  return <div className="ds-root ds-page">
    <h1>Users</h1><p className="text-muted">Passwords are hashed immediately and never returned by the API.</p>
    {error && <div className="ds-banner ds-banner-warn">{error}</div>}
    {resetNotice && <div className="ds-banner" role="status">{resetNotice}</div>}
    {onChangeOwnPassword && <OwnPasswordForm changePassword={onChangeOwnPassword} />}
    {resetTarget && <form className="card form-stack" aria-label={`Reset password for ${resetTarget.user_id}`} onSubmit={(event) => void reset(event)}>
      <h3>Reset password for {resetTarget.display_name}</h3>
      <p className="text-muted">{resetTarget.sign_in_disabled
        ? "Resetting the password restores sign-in."
        : `${resetTarget.user_id} will be signed out of any existing session.`}</p>
      <label>New password<input type="password" value={resetPassword} minLength={12} maxLength={128} required disabled={credentialPending} autoComplete="new-password" onChange={(event) => setResetPassword(event.target.value)} /></label>
      <label>Confirm new password<input type="password" value={resetConfirmation} minLength={12} maxLength={128} required disabled={credentialPending} autoComplete="new-password" onChange={(event) => setResetConfirmation(event.target.value)} /></label>
      <div><button type="submit" className="btn btn-primary" disabled={credentialPending}>Reset password</button> <button type="button" className="btn btn-ghost" disabled={credentialPending} onClick={closeReset}>Cancel</button></div>
    </form>}
    <form className="card form-stack" onSubmit={(event) => void create(event)}>
      <h3>Create user</h3>
      <label>User ID<input value={userId} pattern="[a-z][a-z0-9-]{2,31}" required onChange={(event) => setUserId(event.target.value)} /></label>
      <label>Display name<input value={displayName} minLength={2} maxLength={80} required onChange={(event) => setDisplayName(event.target.value)} /></label>
      <label>Role<select value={role} onChange={(event) => { const next = event.target.value as Role; setRole(next); if (next === "DIRECTOR" || next === "HR" || next === "SUPPORT") setTeamId(""); }}><option value="CLIENT_ONBOARDER">Client onboarder</option><option value="RELATIONSHIP_MANAGER">Relationship manager</option><option value="DIRECTOR">Director</option><option value="HR">Biz Ops</option><option value="SUPPORT">Support</option></select></label>
      {needsTeam && <label>Team<select value={teamId} required onChange={(event) => setTeamId(event.target.value)}><option value="">Select a team</option>{teams.map((team) => <option key={team.team_id} value={team.team_id}>{team.display_name}</option>)}</select></label>}
      <label>Temporary password<input type="password" value={password} minLength={12} maxLength={128} required autoComplete="new-password" onChange={(event) => setPassword(event.target.value)} /></label>
      <label>Confirm password<input type="password" value={passwordConfirmation} minLength={12} maxLength={128} required autoComplete="new-password" onChange={(event) => setPasswordConfirmation(event.target.value)} /></label>
      <button type="submit" className="btn btn-primary">Create user</button>
    </form>
    <div className="table-card table-scroll" tabIndex={0}><table className="table"><thead><tr><th>User</th><th>Role</th><th>Team</th><th>Version</th><th>Action</th></tr></thead><tbody>
      {profiles.map((profile) => <tr key={profile.user_id}>
        <td><strong>{profile.display_name}</strong><div className="text-muted">{profile.user_id}</div></td>
        <td>{roleLabel(profile.role)}</td>
        <td>{profile.team_display_name ?? "Global"}</td>
        <td>{profile.version}</td>
        <td>
          {profile.sign_in_disabled && <div>Sign-in disabled</div>}
          <button type="button" className="btn btn-ghost" disabled={credentialPending} onClick={() => void edit(profile)}>Edit</button>
          {profile.role !== "HR" && <>
            <button type="button" className="btn btn-ghost" disabled={credentialPending} aria-label={`Reset password for ${profile.user_id}`} onClick={() => openReset(profile)}>Reset password</button>
            {!profile.sign_in_disabled && <button type="button" className="btn btn-ghost" disabled={credentialPending} aria-label={`Disable sign-in for ${profile.user_id}`} onClick={() => void disableSignIn(profile)}>Disable sign-in</button>}
          </>}
        </td>
      </tr>)}
    </tbody></table></div>
  </div>;
}

function OwnPasswordForm({ changePassword }: { changePassword: ChangeOwnPassword }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    form.reset();
    if (pending) return;
    const current = String(values.get("current") ?? "");
    const next = String(values.get("new") ?? "");
    if ([current, next].some((password) => [...password].length < 12 || [...password].length > 128)) {
      setError("Enter between 12 and 128 characters for each password.");
      return;
    }
    if (next !== values.get("confirmation")) {
      setError("Password confirmation does not match.");
      return;
    }
    setPending(true);
    setError(null);
    try {
      await changePassword(current, next);
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "Password change failed.");
    } finally {
      setPending(false);
    }
  }

  return <form className="card form-stack" aria-label="Change my password" noValidate onSubmit={(event) => void submit(event)}>
    <h3>Change my password</h3>
    <p className="text-muted">You will sign in again after changing your password.</p>
    {error && <div role="alert" className="ds-banner ds-banner-warn">{error}</div>}
    <label>Current password<input type="password" name="current" required maxLength={128} disabled={pending} autoComplete="current-password" /></label>
    <label>New password<input type="password" name="new" required maxLength={128} disabled={pending} autoComplete="new-password" /></label>
    <label>Confirm new password<input type="password" name="confirmation" required maxLength={128} disabled={pending} autoComplete="new-password" /></label>
    <button type="submit" className="btn btn-primary" disabled={pending}>Change password</button>
  </form>;
}
