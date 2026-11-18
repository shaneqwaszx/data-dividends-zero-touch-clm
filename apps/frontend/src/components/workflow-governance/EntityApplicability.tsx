// C-5 entity applicability PLACEHOLDER (P2-2 addendum, accepted 2026-11-17). Placeholder, not functional.
// Frontend-only: it holds no state, sends nothing and stores nothing. No request, payload, persistence,
// execution, D-136 send hold, fence, mandatory check, GoldTier, policy or UBO effect. Functional,
// add-only applicability is deferred to P2-3 with its own ADR (RR-8).

/**
 * Mirrors the backend RegistryLegalForm enum in apps/backend/app/domain/registry_legal_form.py
 * (system-derived from the registry source value). A parity test reads that file and fails if the
 * two lists differ. No listed-company or financial-institution class exists there, so none is shown.
 */
export const ENTITY_APPLICABILITY_OPTIONS = [
  { value: "COMPANY", label: "Company" },
  { value: "BUSINESS_PARTNERSHIP", label: "Business / partnership" },
  { value: "LLP", label: "LLP" },
  { value: "LP", label: "LP" },
  { value: "GOVERNMENT", label: "Government" },
  { value: "OTHER", label: "Other" },
] as const;

export const ENTITY_APPLICABILITY_EXPLANATION =
  "Later, workflows may add steps for specific entity types, such as checks for verified Government entities. Today every step applies to all entities.";

const COMING_SOON_DESCRIPTION = "Coming soon. This is a placeholder and is not functional yet.";

function ComingSoon({ id }: { id: string }) {
  return <span id={id} className="tag tag-neutral" style={{ marginLeft: 8 }}>Coming soon</span>;
}

/** Workflow-level section: "All entities" is the only selectable value. */
export function EntityApplicabilityPlaceholder() {
  const base = "entity-applicability";
  return (
    <section className="card" aria-labelledby={`${base}-title`} data-testid="entity-applicability-placeholder" style={{ marginTop: 16 }}>
      <h2 id={`${base}-title`} style={{ display: "flex", alignItems: "center" }}>
        Entity applicability<ComingSoon id={`${base}-soon`} />
      </h2>
      <p id={`${base}-desc`} className="text-muted">{ENTITY_APPLICABILITY_EXPLANATION}</p>
      <p id={`${base}-disabled`} className="sr-only">{COMING_SOON_DESCRIPTION}</p>
      <fieldset style={{ border: 0, margin: 0, padding: 0 }} aria-describedby={`${base}-desc`}>
        <legend>Applies to</legend>
        <label style={{ display: "block" }}>
          {/* Uncontrolled and the only value: there is nothing to change and nothing is sent. */}
          <input type="radio" name={`${base}-scope`} value="ALL" defaultChecked /> All entities
        </label>
        {ENTITY_APPLICABILITY_OPTIONS.map(option => (
          <label key={option.value} className="text-muted" style={{ display: "block" }}>
            <input type="radio" name={`${base}-scope`} value={option.value} disabled aria-disabled="true"
              aria-describedby={`${base}-disabled`} /> {option.label}
          </label>
        ))}
      </fieldset>
    </section>
  );
}

/** Step-editor subsection: every control is disabled. */
export function EntityConditionsPlaceholder({ stageName }: { stageName: string }) {
  const base = "entity-conditions";
  return (
    <section aria-labelledby={`${base}-title`} data-testid="entity-conditions-placeholder" style={{ marginTop: 12 }}>
      <p id={`${base}-title`} className="card-kicker" style={{ display: "flex", alignItems: "center" }}>
        Entity-specific conditions<ComingSoon id={`${base}-soon`} />
      </p>
      <p id={`${base}-desc`} className="text-muted">
        "{stageName}" applies to all entities. {ENTITY_APPLICABILITY_EXPLANATION}
      </p>
      <label>Show this step for
        <select className="input" disabled aria-disabled="true" aria-describedby={`${base}-desc ${base}-soon`} value="ALL" onChange={() => undefined}>
          <option value="ALL">All entities</option>
          {ENTITY_APPLICABILITY_OPTIONS.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
      </label>
      <button type="button" className="btn btn-ghost" disabled aria-disabled="true" aria-describedby={`${base}-desc ${base}-soon`}>
        Add condition
      </button>
    </section>
  );
}
