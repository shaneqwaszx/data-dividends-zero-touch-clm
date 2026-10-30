import { useEffect, useState, type FormEvent } from "react";

import { ApiError, createAdminProfile, fetchAdminProfiles, fetchTeamOptions, updateAdminProfile } from "../api";
import type { AdminProfile, AuthenticatedTeam, Role, TeamId } from "../types";

export default function AdminUsers() {
  const [profiles, setProfiles] = useState<AdminProfile[]>([]);
  const [teams, setTeams] = useState<AuthenticatedTeam[]>([]);
  const [userId, setUserId] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState<Role>("CLIENT_ONBOARDER");
  const [teamId, setTeamId] = useState<TeamId | "">("");
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [error, setError] = useState<string | null>(null);
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

  return <div className="ds-root ds-page">
    <h1>Users</h1><p className="text-muted">Passwords are hashed immediately and never returned by the API.</p>
    {error && <div className="ds-banner ds-banner-warn">{error}</div>}
    <form className="card form-stack" onSubmit={(event) => void create(event)}>
      <h3>Create user</h3>
      <label>User ID<input value={userId} pattern="[a-z][a-z0-9-]{2,31}" required onChange={(event) => setUserId(event.target.value)} /></label>
      <label>Display name<input value={displayName} minLength={2} maxLength={80} required onChange={(event) => setDisplayName(event.target.value)} /></label>
      <label>Role<select value={role} onChange={(event) => { const next = event.target.value as Role; setRole(next); if (next === "DIRECTOR" || next === "HR" || next === "SUPPORT") setTeamId(""); }}><option value="CLIENT_ONBOARDER">Client onboarder</option><option value="RELATIONSHIP_MANAGER">Relationship manager</option><option value="DIRECTOR">Director</option><option value="HR">HR</option><option value="SUPPORT">Support</option></select></label>
      {needsTeam && <label>Team<select value={teamId} required onChange={(event) => setTeamId(event.target.value)}><option value="">Select a team</option>{teams.map((team) => <option key={team.team_id} value={team.team_id}>{team.display_name}</option>)}</select></label>}
      <label>Temporary password<input type="password" value={password} minLength={12} maxLength={128} required autoComplete="new-password" onChange={(event) => setPassword(event.target.value)} /></label>
      <label>Confirm password<input type="password" value={passwordConfirmation} minLength={12} maxLength={128} required autoComplete="new-password" onChange={(event) => setPasswordConfirmation(event.target.value)} /></label>
      <button type="submit" className="btn btn-primary">Create user</button>
    </form>
    <div className="table-card table-scroll" tabIndex={0}><table className="table"><thead><tr><th>User</th><th>Role</th><th>Team</th><th>Version</th><th>Action</th></tr></thead><tbody>
      {profiles.map((profile) => <tr key={profile.user_id}><td><strong>{profile.display_name}</strong><div className="text-muted">{profile.user_id}</div></td><td>{profile.role.replaceAll("_", " ")}</td><td>{profile.team_display_name ?? "Global"}</td><td>{profile.version}</td><td><button type="button" className="btn btn-ghost" onClick={() => void edit(profile)}>Edit</button></td></tr>)}
    </tbody></table></div>
  </div>;
}
