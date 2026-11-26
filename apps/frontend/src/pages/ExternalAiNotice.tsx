/**
 * P2-3 (D-129 r3.1 section 4.2): the external-data notice on every chat surface that can reach
 * hosted Claude: the case chat, the general chat, Support chat and "Try with this change", and
 * (D-130 amendment draft, fifth path) the hosted AI insights panel on the dashboard.
 *
 * It is always shown on those surfaces, before anything is typed or tried. The page cannot know
 * for certain whether Claude will be asked (the service decides per call), so the notice never
 * depends on a status read that could fail and hide it.
 *
 * N1: the data is sent when Claude is asked, before its reply is checked. A reply that is refused
 * or discarded is replaced by a labelled answer Claude did not write, but the data has already
 * gone to Anthropic, so the notice says the data is sent even if no Claude answer is shown.
 *
 * What it lists as sent follows the D-129 r3.1 payload inventory for each path. It does not claim
 * that personal information is removed: automatic removal covers only some known identifiers.
 * D-142 Q4 (proposed): it also says that the privacy boundary replaces names, identifiers and
 * unrecognised words with placeholders before sending, and that this is not complete. Each answer
 * an external model wrote says the same in its own attribution (the service's lead notice).
 *
 * D-138 A1 (proposed): it names the provider that can serve the surface, from what the hosted
 * service reports (`external_ai` on the case brief and the health reply): Anthropic for Claude,
 * OpenRouter for GPT-OSS-120B (case chat only, routed to the one approved endpoint), or both
 * whenever both may serve it. The active model is deliberately not used (QG P2-1): HR can switch it
 * while a chat is open, so naming only the active provider could name the wrong recipient. With no
 * report (a development machine, an older service, a failed read) it keeps the Anthropic wording it
 * always had. The report only chooses words; the notice is
 * always shown, and the service alone decides what is sent.
 */

import { useId, useState } from "react";

import type { ExternalAiStatus } from "../aiAssistant";

export type ExternalAiSurface = "case" | "general" | "support" | "try" | "insights";

const WHEN: Record<ExternalAiSurface, string> = {
  case: "in this chat",
  general: "in this chat",
  support: "in this chat",
  try: "for Try with this change",
  insights: "for AI insights",
};

// D-129 r3.1 sections 2A to 2D: the user-visible parts of each path's request.
const SENT: Record<ExternalAiSurface, string> = {
  case: "your question, this chat's earlier messages and this case's details",
  general: "your question and this chat's earlier messages",
  support: "your question, this chat's earlier messages and the active policy rules",
  try: "the title and text of this change, the conversation's first question and this case's details",
  // D-130 amendment draft: only figures the service derives from the eligible cases.
  insights: "counts and status labels from the eligible cases on this dashboard (no names, teams or case identifiers)",
};

/** Who the notice names: one provider, or either of the two hosted ones. */
export type ExternalAiNamed = "anthropic" | "openrouter" | "either";

const KNOWN = new Set(["anthropic", "openrouter"]);

/**
 * The provider a surface's notice names, from the service's report. Unknown values are ignored;
 * a missing or malformed report keeps the original Anthropic wording.
 */
export function noticeProvider(surface: ExternalAiSurface, status?: ExternalAiStatus | null): ExternalAiNamed {
  if (!status || !Array.isArray(status.providers) || typeof status.surfaces !== "object" || !status.surfaces) {
    return "anthropic";
  }
  const serving = status.providers.filter(
    (name) => KNOWN.has(name) && Array.isArray(status.surfaces[name]) && status.surfaces[name].includes(surface),
  ) as Array<"anthropic" | "openrouter">;
  // QG P2-1: never only the active one when another may also serve this surface. HR can switch
  // the active model while a chat is open, and the report is read once per brief or health call.
  if (serving.length === 1) return serving[0];
  if (serving.length > 1) return "either";
  return "anthropic";
}

const TAIL =
  "Use synthetic test data only. Do not enter real " +
  "names, contact details, ID numbers or any other personal or confidential information. Automatic " +
  "removal covers only some known identifiers, not everything you type. Before anything is sent, " +
  "names, identifiers and words the service does not recognise are replaced with placeholders, " +
  "and restored only here (D-142); this cannot catch every way of writing personal information.";

/** The notice's plain text for a surface (also used by the tests). */
export function externalAiNoticeText(surface: ExternalAiSurface, named: ExternalAiNamed = "anthropic"): string {
  if (named === "openrouter") {
    return (
      `When GPT-OSS-120B (OpenRouter) is asked ${WHEN[surface]}, ${SENT[surface]} are sent to OpenRouter, ` +
      "an external AI provider outside this application, which routes them to the one approved " +
      "GPT-OSS-120B endpoint. They are sent even if no GPT-OSS-120B answer is shown to you. " +
      TAIL
    );
  }
  if (named === "either") {
    return (
      `When an external AI model is asked ${WHEN[surface]}, ${SENT[surface]} are sent to its provider, ` +
      "outside this application: Anthropic for Claude, or OpenRouter (routed to the one approved " +
      "GPT-OSS-120B endpoint) for GPT-OSS-120B. They are sent even if no AI answer is shown to you. " +
      TAIL
    );
  }
  return (
    `When Claude (Anthropic) is asked ${WHEN[surface]}, ${SENT[surface]} are sent to Anthropic, ` +
    "an external AI provider outside this application. They are sent even if no Claude answer is shown " +
    "to you. " +
    TAIL
  );
}

// Compact notice (FYP demonstration, owner-approved): the summary is always visible, collapsed or
// not, and on its own still says what is sent, to which provider, that it is sent even if no
// answer is shown, and that the placeholder replacement is not complete. Expanding adds the full
// text below it, unchanged. The control is a native button with aria-expanded (keyboard operable).
const SUMMARY_TAIL = "Names and identifiers are replaced with placeholders first, but this is not complete.";

/** The always-visible summary line for a surface (also used by the tests). */
export function externalAiNoticeSummary(surface: ExternalAiSurface, named: ExternalAiNamed = "anthropic"): string {
  if (named === "openrouter") {
    return (
      `When GPT-OSS-120B (OpenRouter) is asked ${WHEN[surface]}, ${SENT[surface]} are sent to OpenRouter, ` +
      `even if no GPT-OSS-120B answer is shown. ${SUMMARY_TAIL}`
    );
  }
  if (named === "either") {
    return (
      `When an external AI model is asked ${WHEN[surface]}, ${SENT[surface]} are sent to Anthropic (Claude) ` +
      `or OpenRouter (GPT-OSS-120B), even if no AI answer is shown. ${SUMMARY_TAIL}`
    );
  }
  return (
    `When Claude (Anthropic) is asked ${WHEN[surface]}, ${SENT[surface]} are sent to Anthropic, ` +
    `even if no Claude answer is shown. ${SUMMARY_TAIL}`
  );
}

export default function ExternalAiNotice({
  surface,
  id,
  status,
}: {
  surface: ExternalAiSurface;
  id?: string;
  /** D-138 A1: the service's external AI report, when the page has one. */
  status?: ExternalAiStatus | null;
}) {
  const named = noticeProvider(surface, status);
  const [open, setOpen] = useState(false);
  const detailsId = `${useId()}-details`;
  return (
    <div className="ai-external-notice" id={id} data-testid="external-ai-notice" data-surface={surface} data-provider={named}>
      <p className="ai-external-notice__summary" data-testid="external-ai-notice-summary">
        <strong>External AI · synthetic data only.</strong> {externalAiNoticeSummary(surface, named)}{" "}
        <button
          type="button"
          className="ai-external-notice__toggle"
          aria-expanded={open}
          aria-controls={detailsId}
          onClick={() => setOpen((value) => !value)}
        >
          {open ? "Hide full notice" : "Show full notice"}
        </button>
      </p>
      <p className="ai-external-notice__details" id={detailsId} data-testid="external-ai-notice-details" hidden={!open}>
        {externalAiNoticeText(surface, named)}
      </p>
    </div>
  );
}
