import { useId, useState } from "react";

import { displayTimestamp } from "../shared";
import type { EntityTypeBasis, GovernmentBodyType } from "../types";

/** D-125: what the RM keys in; the server compares the statute with the document. */
export interface GovernmentStatuteInput {
  founding_statute: string;
  statute_section: string | null;
  government_body_type: GovernmentBodyType;
}

export const GOVERNMENT_BODY_TYPE_LABELS: Record<GovernmentBodyType, string> = {
  MINISTRY_OR_ORGAN_OF_STATE: "Ministry or Organ of State",
  STATUTORY_BOARD: "Statutory Board",
};

const STATUTE_MIN = 3;
const STATUTE_MAX = 200;
const SECTION_MAX = 40;

/** D-101: replaces the ownership/UBO step for a Singapore Government entity. Server-owned state. */
export default function GovernmentStatusPanel({ basis, canConfirm, disabled, onConfirm, onContinue }: {
  basis: EntityTypeBasis;
  canConfirm: boolean;
  disabled: boolean;
  /** Resolves true when the server rejected the statute as not matching the document. */
  onConfirm: (input: GovernmentStatuteInput) => Promise<boolean>;
  /** D-125: the existing resume, offered only when the server says the step must reopen. */
  onContinue: () => void;
}) {
  const status = basis.government_status;
  const ids = useId();
  const [statute, setStatute] = useState("");
  const [section, setSection] = useState("");
  const [bodyType, setBodyType] = useState<GovernmentBodyType | null>(null);
  const [mismatch, setMismatch] = useState(false);
  const trimmedStatute = statute.trim();
  const trimmedSection = section.trim();
  const ready = trimmedStatute.length >= STATUTE_MIN && trimmedStatute.length <= STATUTE_MAX
    && trimmedSection.length <= SECTION_MAX && bodyType !== null;

  async function submit() {
    if (!ready || bodyType === null) return;
    setMismatch(false);
    const rejected = await onConfirm({
      founding_statute: trimmedStatute,
      statute_section: trimmedSection || null,
      government_body_type: bodyType,
    });
    setMismatch(rejected);
  }

  return <section className="manual-ownership" aria-labelledby="government-status-title">
    <p className="card-kicker">Government status · local proof of concept</p>
    <h2 id="government-status-title">Singapore Government status</h2>
    <p className="manual-ownership__source">{basis.label}</p>
    <p>For a Singapore Government entity, no ownership or UBO analysis applies. Confirm only after you have reviewed the status document. This confirmation is not approval and claims no ACRA verification.</p>
    {status?.state === "EVIDENCE_REQUIRED" && <p className="ds-banner ds-banner-warn" role="status">
      No current reviewed document shows every required label. Upload a status letter with the legal name, UEN, founding Act or Gazette (Founding Instrument), KYC Customer Type: Government and Client Segment: DI - Government.
    </p>}
    {status && status.state !== "EVIDENCE_REQUIRED" && <dl className="document-field__evidence">
      <dt>Founding instrument (from document)</dt><dd>{status.founding_instrument}</dd>
      <dt>Status document version</dt><dd>{status.document_event_count}</dd>
      {status.state === "CONFIRMED" && <>
        <dt>Founding statute (RM-entered)</dt><dd>{status.founding_statute ?? "—"}</dd>
        <dt>Section</dt><dd>{status.statute_section ?? "—"}</dd>
        <dt>Type of body</dt><dd>{status.government_body_type ? GOVERNMENT_BODY_TYPE_LABELS[status.government_body_type] : "—"}</dd>
        <dt>Matched to document</dt><dd>{status.statute_match === "MATCHED_AFTER_NORMALISATION" ? "Yes" : "—"}</dd>
        <dt>Confirmed by</dt><dd>{status.confirmed_by_actor_id}</dd>
        <dt>Confirmed at</dt><dd>{status.confirmed_at ? displayTimestamp(status.confirmed_at) : "—"}</dd>
      </>}
    </dl>}
    {status?.state === "CONFIRMED" && <p className="ds-banner" role="status">Government status confirmed from the reviewed document.</p>}
    {status?.state === "CONFIRMATION_REQUIRED" && status.resume_required === true && (canConfirm
      ? <div className="ds-banner ds-banner-warn" role="status">
        <p>This Government status was confirmed before the founding statute was recorded, so it no longer counts. Continue onboarding to reopen the Government status step, then confirm it again with the statute.</p>
        <button type="button" className="btn btn-primary" disabled={disabled} onClick={onContinue}>Continue onboarding</button>
      </div>
      : <p role="status">Only the case creator can confirm Government status.</p>)}
    {status?.state === "CONFIRMATION_REQUIRED" && status.resume_required !== true && (canConfirm
      ? <form className="government-statute" aria-label="Confirm Government status" noValidate onSubmit={(event) => { event.preventDefault(); void submit(); }}>
        <div className="manual-ownership__fields">
          <label>Founding statute
            <input className="input" name="founding_statute" value={statute} required minLength={STATUTE_MIN} maxLength={STATUTE_MAX} disabled={disabled} aria-describedby={`${ids}-statute-help`} aria-invalid={mismatch || undefined} onChange={(event) => { setStatute(event.target.value); setMismatch(false); }} />
            <span id={`${ids}-statute-help`} className="control-help">Type the Act that established this body, as shown on the status document (e.g. 'Demo Parks FYP Test Authority Act').</span>
          </label>
          <label>Section (optional)
            <input className="input" name="statute_section" value={section} maxLength={SECTION_MAX} disabled={disabled} placeholder="e.g. s 3" onChange={(event) => setSection(event.target.value)} />
          </label>
        </div>
        <fieldset className="government-statute__body" disabled={disabled}>
          <legend>Type of body</legend>
          {(Object.keys(GOVERNMENT_BODY_TYPE_LABELS) as GovernmentBodyType[]).map((value) => <label key={value}>
            <input type="radio" name={`${ids}-government_body_type`} value={value} checked={bodyType === value} onChange={() => setBodyType(value)} />
            {GOVERNMENT_BODY_TYPE_LABELS[value]}
          </label>)}
        </fieldset>
        {mismatch && <p className="ds-banner ds-banner-warn" role="alert">
          The statute you entered does not match the Founding Instrument on the reviewed document: "{status.founding_instrument}". Check the document, or upload a corrected status letter.
        </p>}
        <button type="submit" className="btn btn-primary" disabled={disabled || !ready}>Confirm Government status</button>
      </form>
      : <p role="status">Only the case creator can confirm Government status.</p>)}
    <p className="control-help">Authorised signatories appear on the status document only. They are not extracted, stored as an ownership graph or sent to GoldTier.</p>
  </section>;
}
