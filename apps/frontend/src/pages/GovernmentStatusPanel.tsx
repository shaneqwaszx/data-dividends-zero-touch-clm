import { displayTimestamp } from "../shared";
import type { EntityTypeBasis } from "../types";

/** D-101: replaces the ownership/UBO step for a Singapore Government entity. Server-owned state. */
export default function GovernmentStatusPanel({ basis, canConfirm, disabled, onConfirm }: {
  basis: EntityTypeBasis;
  canConfirm: boolean;
  disabled: boolean;
  onConfirm: () => void;
}) {
  const status = basis.government_status;
  return <section className="manual-ownership" aria-labelledby="government-status-title">
    <p className="card-kicker">Government status · local proof of concept</p>
    <h2 id="government-status-title">Singapore Government status</h2>
    <p className="manual-ownership__source">{basis.label}</p>
    <p>For a Singapore Government entity, no ownership or UBO analysis applies. Confirm only after you have reviewed the status document. This confirmation is not approval and claims no ACRA verification.</p>
    {status?.state === "EVIDENCE_REQUIRED" && <p className="ds-banner ds-banner-warn" role="status">
      No current reviewed document shows every required label. Upload a status letter with the legal name, UEN, founding Act or Gazette (Founding Instrument), KYC Customer Type: Government and Client Segment: DI - Government.
    </p>}
    {status && status.state !== "EVIDENCE_REQUIRED" && <dl className="document-field__evidence">
      <dt>Founding instrument</dt><dd>{status.founding_instrument}</dd>
      <dt>Status document version</dt><dd>{status.document_event_count}</dd>
      {status.state === "CONFIRMED" && <>
        <dt>Confirmed by</dt><dd>{status.confirmed_by_actor_id}</dd>
        <dt>Confirmed at</dt><dd>{status.confirmed_at ? displayTimestamp(status.confirmed_at) : "—"}</dd>
      </>}
    </dl>}
    {status?.state === "CONFIRMED" && <p className="ds-banner" role="status">Government status confirmed from the reviewed document.</p>}
    {status?.state === "CONFIRMATION_REQUIRED" && (canConfirm
      ? <button type="button" className="btn btn-primary" disabled={disabled} onClick={onConfirm}>Confirm Government status</button>
      : <p role="status">Only the case creator can confirm Government status.</p>)}
    <p className="control-help">Authorised signatories appear on the status document only. They are not extracted, stored as an ownership graph or sent to GoldTier.</p>
  </section>;
}
