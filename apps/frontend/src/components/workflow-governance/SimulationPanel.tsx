import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import type { WorkflowStage } from "../../workflowApi";
import {
  fetchSimulationScenarios,
  governanceRefusal,
  simulateProposal,
  workflowGovernanceQueryKeys,
  type GovernanceRefusal,
} from "../../workflowGovernanceApi";
import type { SimulationResult } from "../../workflowGovernanceTypes";
import { GovernanceRefusalPanel, SimulationResultPanel } from "./GovernancePanels";

/** Synthetic only: a fixed server-side scenario catalogue; no case, provider or GoldTier call. */
export function SimulationPanel({ userId, workflowId, proposalId, stages }: {
  userId: string; workflowId: string; proposalId: string; stages: WorkflowStage[];
}) {
  const scenarios = useQuery({
    queryKey: workflowGovernanceQueryKeys.scenarios(userId),
    queryFn: ({ signal }) => fetchSimulationScenarios(signal),
    retry: false,
  });
  const [chosen, setChosen] = useState<string[]>([]);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [refusal, setRefusal] = useState<GovernanceRefusal | null>(null);
  const [running, setRunning] = useState(false);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);

  async function run() {
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;
    setRunning(true);
    setRefusal(null);
    try {
      const next = await simulateProposal(workflowId, proposalId, { stages, scenario_ids: chosen }, current.signal);
      if (!current.signal.aborted) setResult(next);
    } catch (error) {
      if (!current.signal.aborted) setRefusal(governanceRefusal(error));
    } finally {
      if (controller.current === current) setRunning(false);
    }
  }

  return (
    <section className="card" aria-labelledby="simulation-title" data-testid="simulation-panel" style={{ marginBottom: 16 }}>
      <h2 id="simulation-title">Simulation <span className="tag tag-neutral">Synthetic</span></h2>
      <p className="text-muted">
        Synthetic simulation: fictional companies from a fixed catalogue. No case, document, provider or GoldTier call is read or made, and nothing is saved.
      </p>
      {scenarios.isPending && <p className="text-muted">Loading synthetic scenarios…</p>}
      {scenarios.isError && <GovernanceRefusalPanel refusal={governanceRefusal(scenarios.error)} />}
      {scenarios.data && (
        <fieldset style={{ border: 0, margin: 0, padding: 0 }}>
          <legend>Synthetic scenarios (none chosen runs them all)</legend>
          {scenarios.data.map(item => (
            <label key={item.scenario_id} style={{ display: "block" }}>
              <input type="checkbox" checked={chosen.includes(item.scenario_id)}
                onChange={event => setChosen(event.target.checked ? [...chosen, item.scenario_id] : chosen.filter(id => id !== item.scenario_id))} />
              {" "}{item.label} (synthetic)
            </label>
          ))}
        </fieldset>
      )}
      <button type="button" className="btn btn-secondary" style={{ marginTop: 8 }} disabled={running || !scenarios.data} onClick={() => void run()}>
        Run synthetic simulation
      </button>
      {refusal && <GovernanceRefusalPanel refusal={refusal} />}
      {result && <SimulationResultPanel result={result} />}
    </section>
  );
}
