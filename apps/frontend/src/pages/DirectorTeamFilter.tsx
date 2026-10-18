import { useEffect, useState } from "react";

import { fetchTeamOptions } from "../api";
import type { AuthenticatedProfile, AuthenticatedTeam } from "../types";

export default function DirectorTeamFilter({ actor, value, onChange }: {
  actor: AuthenticatedProfile;
  value: string;
  onChange: (value: string) => void;
}) {
  const [teams, setTeams] = useState<AuthenticatedTeam[]>([]);

  useEffect(() => {
    if (actor.role === "DIRECTOR") void fetchTeamOptions().then(setTeams).catch(() => setTeams([]));
  }, [actor.role]);

  if (actor.role !== "DIRECTOR") return null;
  return <label className="director-team-filter"><span>Team scope</span><select aria-label="Team scope" value={value} onChange={(event) => onChange(event.target.value)}><option value="all">All teams</option><option value="unassigned">Legacy unassigned</option>{teams.map((team) => <option key={team.team_id} value={team.team_id}>{team.display_name} · {team.client_scope_label}</option>)}</select></label>;
}
