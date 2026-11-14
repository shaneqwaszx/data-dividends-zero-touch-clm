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
 */

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

/** The notice's plain text for a surface (also used by the tests). */
export function externalAiNoticeText(surface: ExternalAiSurface): string {
  return (
    `When Claude (Anthropic) is asked ${WHEN[surface]}, ${SENT[surface]} are sent to Anthropic, ` +
    "an external AI provider outside this application. They are sent even if no Claude answer is shown " +
    "to you. Use synthetic test data only. Do not enter real " +
    "names, contact details, ID numbers or any other personal or confidential information. Automatic " +
    "removal covers only some known identifiers, not everything you type."
  );
}

export default function ExternalAiNotice({ surface, id }: { surface: ExternalAiSurface; id?: string }) {
  return (
    <p className="ai-external-notice" id={id} data-testid="external-ai-notice" data-surface={surface}>
      <strong>External AI · synthetic data only.</strong> {externalAiNoticeText(surface)}
    </p>
  );
}
