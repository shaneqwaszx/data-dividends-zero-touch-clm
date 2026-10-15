import { parseCaseId } from "../navigation";

export interface AiAssistantContext {
  /** The case the AI assistant talks about, or null when there is none to explain yet. */
  caseId: string | null;
  /** On New onboarding before its case exists, the AI assistant asks for the company first. */
  onboardingWithoutCase: boolean;
}

function caseIdSegment(segment: string | undefined): string | null {
  if (!segment) return null;
  let decoded = segment;
  try {
    decoded = decodeURIComponent(segment);
  } catch {
    // parseCaseId rejects anything malformed
  }
  return parseCaseId(decoded);
}

/**
 * The AI assistant answers once the system has replied for a case:
 * - on a case's page under Cases (/cases/:caseId);
 * - on New onboarding once its case has been created (the live intake case, or
 *   /new-onboarding/:caseId when an intake is resumed).
 * Everywhere else there is no case for it to explain.
 */
export function aiAssistantContextFor(pathname: string, intakeCaseId: string | null): AiAssistantContext {
  const [first, second, ...rest] = pathname.split("/").filter(Boolean);
  if (rest.length > 0) return { caseId: null, onboardingWithoutCase: false };
  if (first === "cases") return { caseId: caseIdSegment(second), onboardingWithoutCase: false };
  if (first === "new-onboarding") {
    const caseId = second ? caseIdSegment(second) : caseIdSegment(intakeCaseId ?? undefined);
    return { caseId, onboardingWithoutCase: caseId === null };
  }
  return { caseId: null, onboardingWithoutCase: false };
}
