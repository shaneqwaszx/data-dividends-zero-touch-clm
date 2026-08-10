import { useEffect, useState, type FormEvent } from "react";

import { createOnboardingCase, fetchMockScenarios } from "./api";
import type { MockScenario, OnboardingCase, SimulationProfile } from "./types";

const DEFAULT_UEN = "202400001A";

function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat("en-SG", {
    dateStyle: "medium",
    timeStyle: "medium",
    timeZone: "Asia/Singapore",
  }).format(new Date(value));
}

function formatAddress(caseData: OnboardingCase): string {
  const address = caseData.entity?.registered_address;
  if (!address) return "Not available";
  return [address.address_line_1, address.address_line_2, address.postal_code]
    .filter(Boolean)
    .join(", ");
}

export function SimulationBanner({ profile }: { profile: SimulationProfile | null }) {
  return (
    <div className="environment-banner" role="status">
      <span aria-hidden="true" />
      {profile
        ? `Simulated environment · ${profile.registry_system} (${profile.registry_environment}) + ${profile.target_system} (${profile.target_environment}) · No real customer data`
        : "Simulated environment · Loading backend simulation profile…"}
    </div>
  );
}

export function CaseSummary({ caseData }: { caseData: OnboardingCase }) {
  const terminalTone =
    caseData.state === "COMPLETED"
      ? "success"
      : caseData.state === "REVIEW_REQUIRED"
        ? "review"
        : caseData.state === "FAILED"
          ? "failed"
          : "active";

  return (
    <section className="result-panel" aria-live="polite" aria-labelledby="case-heading">
      <div className={`case-status case-status--${terminalTone}`}>
        <span>Current case state</span>
        <strong>{caseData.state}</strong>
      </div>

      <div className="panel-grid">
        <article className="detail-card">
          <p className="section-label">Canonical company</p>
          <h2 id="case-heading">{caseData.entity?.legal_name ?? caseData.requested_uen}</h2>
          <dl>
            <div>
              <dt>UEN</dt>
              <dd>{caseData.entity?.registration_number ?? caseData.requested_uen}</dd>
            </div>
            <div>
              <dt>Country</dt>
              <dd>{caseData.entity?.country_of_incorporation ?? "Not available"}</dd>
            </div>
            <div>
              <dt>Entity type</dt>
              <dd>{caseData.entity?.party_type ?? "Not available"}</dd>
            </div>
            <div>
              <dt>Registered address</dt>
              <dd>{formatAddress(caseData)}</dd>
            </div>
            <div>
              <dt>Registry source</dt>
              <dd>
                {caseData.entity
                  ? `${caseData.entity.source.source_system} · ${caseData.entity.source.environment}`
                  : "Not available"}
              </dd>
            </div>
          </dl>
        </article>

        <article className="detail-card">
          <p className="section-label">Mock GoldTier result</p>
          {caseData.goldtier_result ? (
            <dl>
              <div>
                <dt>Party ID</dt>
                <dd>{caseData.goldtier_result.party_id}</dd>
              </div>
              <div>
                <dt>Shell</dt>
                <dd>{caseData.goldtier_result.shell_status}</dd>
              </div>
              <div>
                <dt>Policy</dt>
                <dd>{caseData.goldtier_result.policy_status ?? "Not created"}</dd>
              </div>
              <div>
                <dt>Amend</dt>
                <dd>{caseData.goldtier_result.amend_status ?? "Not attempted"}</dd>
              </div>
            </dl>
          ) : (
            <p className="empty-copy">No mock GoldTier customer was created.</p>
          )}
        </article>
      </div>

      {caseData.error && (
        <div className={`outcome-message outcome-message--${terminalTone}`} role="status">
          <strong>{caseData.error.code}</strong>
          <span>{caseData.error.message}</span>
        </div>
      )}

      <article className="timeline-card">
        <div className="timeline-heading">
          <div>
            <p className="section-label">Safe case history</p>
            <h2>Workflow progression</h2>
          </div>
          <span>{caseData.events.length} events</span>
        </div>
        <ol className="timeline">
          {caseData.events.map((event) => (
            <li key={event.sequence} className={`timeline-item timeline-item--${event.outcome}`}>
              <span className="timeline-marker" aria-hidden="true" />
              <div>
                <div className="timeline-state">
                  <strong>{event.stage}</strong>
                  <span>{event.outcome}</span>
                </div>
                <p>{event.message}</p>
                <time dateTime={event.timestamp}>{formatTimestamp(event.timestamp)}</time>
              </div>
            </li>
          ))}
        </ol>
      </article>

      <p className="case-identifiers">
        Case {caseData.case_id} · Correlation {caseData.correlation_id}
      </p>
    </section>
  );
}

export default function App() {
  const [uen, setUen] = useState(DEFAULT_UEN);
  const [scenarios, setScenarios] = useState<MockScenario[]>([]);
  const [simulationProfile, setSimulationProfile] = useState<SimulationProfile | null>(null);
  const [caseData, setCaseData] = useState<OnboardingCase | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);

  useEffect(() => {
    void fetchMockScenarios()
      .then((discovery) => {
        setScenarios(discovery.scenarios);
        setSimulationProfile(discovery.simulation);
      })
      .catch(() => setRequestError("Mock scenario discovery is unavailable."));
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setRequestError(null);
    setCaseData(null);
    try {
      setCaseData(await createOnboardingCase(uen));
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Unable to start onboarding.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="page-shell">
      <header className="hero">
        <SimulationBanner profile={simulationProfile} />
        <p className="eyebrow">Data Dividends · Phase 01</p>
        <h1>Singapore onboarding, end to end.</h1>
        <p className="summary">
          Start a synthetic case and follow its data from the registry boundary through the
          canonical model into a credential-free GoldTier simulation.
        </p>
      </header>

      <section className="launch-card" aria-labelledby="launch-heading">
        <div>
          <p className="section-label">Mock case launcher</p>
          <h2 id="launch-heading">Choose a synthetic UEN</h2>
          <p>Known scenarios are selectable, and any other value exercises the not-found path.</p>
        </div>
        <form onSubmit={(event) => void handleSubmit(event)}>
          <label htmlFor="uen">Singapore UEN</label>
          <div className="form-row">
            <input
              id="uen"
              name="uen"
              list="mock-uens"
              value={uen}
              onChange={(event) => setUen(event.target.value.toUpperCase())}
              maxLength={64}
              required
              autoComplete="off"
            />
            <datalist id="mock-uens">
              {scenarios.map((scenario) => (
                <option key={scenario.uen} value={scenario.uen}>
                  {scenario.label} — {scenario.expected_outcome}
                </option>
              ))}
            </datalist>
            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Running mock flow…" : "Start onboarding"}
            </button>
          </div>
          <p className="input-help">
            Try {DEFAULT_UEN} for the happy path or select another synthetic scenario.
          </p>
        </form>
      </section>

      {requestError && (
        <div className="request-error" role="alert">
          {requestError}
        </div>
      )}
      {caseData && <CaseSummary caseData={caseData} />}
    </main>
  );
}
