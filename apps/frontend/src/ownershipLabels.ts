import { formatOwnershipCalculation, formatOwnershipPercent } from "./ownershipDisplay";
import type { OwnershipCandidate } from "./types";

/*
 * Presentation only: plain-language wording for backend ownership results.
 * Every function reads the backend's own result and never compares percentages,
 * so the threshold comparison stays the backend's (D-022). The wording mirrors the
 * AI assistant's existing phrasing (apps/assistant/ai_assistant/copilot.py).
 */

type ThresholdResult = OwnershipCandidate["threshold_result"];
type Classification = OwnershipCandidate["classification"];
type PartyType = OwnershipCandidate["party"]["party_type"];

const CLASSIFICATION_TEXT: Record<Classification, string> = {
  PROVISIONAL_UBO_CANDIDATE: "Provisional UBO candidate (meets the threshold; not verified)",
  BELOW_PROVISIONAL_THRESHOLD: "Below the threshold",
  REVIEW_REQUIRED: "Needs a person's review before any conclusion",
  INDETERMINATE: "Cannot be determined from the available records",
};

/** The backend classification in plain language; an unknown value is shown as received. */
export function classificationText(classification: Classification | string): string {
  return CLASSIFICATION_TEXT[classification as Classification] ?? String(classification);
}

/** "≥" for the inclusive comparator; any other comparator is shown as received. */
export function comparatorSymbol(comparator: string): string {
  return comparator === "GREATER_THAN_OR_EQUAL_TO" ? "≥" : comparator;
}

function thresholdPhrase(thresholdPercent: string, comparator: string): string {
  const threshold = formatOwnershipPercent(thresholdPercent);
  return comparator === "GREATER_THAN_OR_EQUAL_TO"
    ? `the ${threshold} threshold (${threshold} or more)`
    : `the ${comparatorSymbol(comparator)} ${threshold} threshold`;
}

/** The backend threshold result in plain language. MET/NOT_MET are never recomputed here. */
export function thresholdResultText(
  result: ThresholdResult | string | null | undefined,
  thresholdPercent: string,
  comparator: string,
): string {
  if (result === "MET") return `Meets ${thresholdPhrase(thresholdPercent, comparator)}`;
  if (result === "NOT_MET") {
    return comparator === "GREATER_THAN_OR_EQUAL_TO"
      ? `Below the ${formatOwnershipPercent(thresholdPercent)} threshold`
      : `Does not meet ${thresholdPhrase(thresholdPercent, comparator)}`;
  }
  if (result === "INDETERMINATE") return "Cannot be determined from the available records";
  return result == null ? "Not available" : String(result);
}

/** "Individual" or "Company"-style party type for people reading the case, not engine names. */
export function partyTypeText(partyType: PartyType | string | null | undefined): string {
  if (partyType === "NATURAL_PERSON") return "Individual";
  if (partyType === "LEGAL_ENTITY") return "Legal entity";
  return partyType ? String(partyType).replaceAll("_", " ") : "Unknown type";
}

/**
 * One retained relationship as "Owner owns N% of Owned entity". In the backend graph the
 * parent is the owned entity and the child is its holder.
 */
export function ownershipStatement(ownerName: string, ownedName: string, ownershipPercent: string | null | undefined): string {
  const percent = formatOwnershipPercent(ownershipPercent);
  return `${ownerName} owns ${percent === "Not available" ? "an unreported share" : percent} of ${ownedName}`;
}

/** The backend calculation text with rounded percentages and a multiplication sign. */
export function calculationText(calculation: string): string {
  return formatOwnershipCalculation(calculation).replace(/ x /g, " × ");
}

/** Analysis state as a short status for the explorer header. */
export function analysisStateText(state: string): string {
  if (state === "ANALYZED") return "Calculated";
  if (state === "REVIEW_REQUIRED") return "Needs review";
  return state.replaceAll("_", " ");
}
