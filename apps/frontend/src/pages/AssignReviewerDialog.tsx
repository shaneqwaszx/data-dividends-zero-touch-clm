import { useState } from "react";

import type { ZeroTouchCaseSummary, ZeroTouchException } from "../types";

export default function AssignReviewerDialog({
  summary,
  exception,
  onClose,
  onAssigned,
}: {
  summary: ZeroTouchCaseSummary;
  exception: ZeroTouchException;
  onClose: () => void;
  onAssigned: (summary: ZeroTouchCaseSummary) => void;
}) {
  const [note, setNote] = useState("");
  void summary;
  void onAssigned;

  return (
    <div className="ds-root dialog-backdrop" role="dialog" aria-modal="true" aria-labelledby="assign-reviewer-title">
      <div className="dialog">
        <p className="card-kicker">{exception.stage.replaceAll("_", " ")} exception</p>
        <h2 id="assign-reviewer-title" className="dialog-title">Assign reviewer</h2>
        <p className="dialog-body">{exception.explanation}</p>
        <div className="field">
          <label htmlFor="reviewer-select">Reviewer</label>
          <select
            id="reviewer-select"
            className="input"
            value=""
            disabled
            onChange={() => undefined}
          >
            <option value="">Not available in current POC</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="assign-note">Note — optional</label>
          <textarea
            id="assign-note"
            className="input"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            maxLength={240}
            disabled
          />
        </div>
        <div className="ds-banner ds-banner-warn">Reviewer assignment is not available in current POC.</div>
        <div className="dialog-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled
            title="Not available in current POC"
          >
            Assign
          </button>
        </div>
      </div>
    </div>
  );
}
