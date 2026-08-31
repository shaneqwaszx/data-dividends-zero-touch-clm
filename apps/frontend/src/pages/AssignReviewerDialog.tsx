import { useEffect, useState } from "react";

import { assignReviewer, fetchReviewers } from "../api";
import type { Reviewer, ZeroTouchCaseSummary, ZeroTouchException } from "../types";

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
  const [reviewers, setReviewers] = useState<Reviewer[]>([]);
  const [reviewerId, setReviewerId] = useState("");
  const [note, setNote] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchReviewers()
      .then(setReviewers)
      .catch(() => setError("The reviewer directory is unavailable."));
  }, []);

  async function handleAssign() {
    if (!reviewerId) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const updated = await assignReviewer(summary, exception.exception_id, reviewerId, note || undefined);
      onAssigned(updated);
    } catch (assignError) {
      setError(assignError instanceof Error ? assignError.message : "Assignment failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

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
            value={reviewerId}
            onChange={(event) => setReviewerId(event.target.value)}
          >
            <option value="">Select a reviewer…</option>
            {reviewers.map((reviewer) => (
              <option key={reviewer.reviewer_id} value={reviewer.reviewer_id}>
                {reviewer.display_name} — {reviewer.open_exception_count} open exception
                {reviewer.open_exception_count === 1 ? "" : "s"}
              </option>
            ))}
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
          />
        </div>
        {error && <div className="ds-banner ds-banner-warn">{error}</div>}
        <div className="dialog-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={isSubmitting || !reviewerId}
            onClick={() => void handleAssign()}
          >
            {isSubmitting ? "Assigning…" : "Assign"}
          </button>
        </div>
      </div>
    </div>
  );
}
