import type { OwnershipAnalysisRecord, OwnershipCandidate } from "./types";

/** Presentation only: never use these labels for arithmetic or classification. */
export function formatOwnershipPercent(value: string | null | undefined): string {
  if (value == null) return "Not available";
  const match = /^(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?$/.exec(value);
  if (!match) return "Not available";
  const fraction = match[2] ?? "";
  const digits = match[1] + fraction;
  if (!/[1-9]/.test(digits)) return "0%";
  // Locate the hundredths boundary without converting the Decimal to a float.
  const boundary = BigInt(match[1].length) + BigInt(match[3] ?? "0") + 2n;
  if (boundary < 0n) return "<0.01%";
  const retained = boundary >= BigInt(digits.length)
    ? digits + "0".repeat(Number(boundary - BigInt(digits.length)))
    : digits.slice(0, Number(boundary));
  const roundingDigit = boundary < BigInt(digits.length) ? digits[Number(boundary)] : "0";
  const cents = BigInt(retained || "0") + (roundingDigit >= "5" ? 1n : 0n);
  if (cents === 0n) return "<0.01%";
  const decimals = (cents % 100n).toString().padStart(2, "0").replace(/0+$/, "");
  return `${cents / 100n}${decimals ? `.${decimals}` : ""}%`;
}

// Backend calculation text retains its operators; only percentage tokens are rounded.
export function formatOwnershipCalculation(value: string): string {
  return value.replace(/\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?%/g, token => formatOwnershipPercent(token.slice(0, -1)));
}

// D-081 presentation: only the backend's own assumed-basis result is read, never a local
// comparison. Formal provisional UBOs stay keyed on `classification` alone.
export function hasAssumedBasisComparison(record: OwnershipAnalysisRecord | null | undefined): boolean {
  return record?.candidates.some(candidate => candidate.synthetic_basis_threshold_result != null) ?? false;
}

export function assumedBasisMatches(record: OwnershipAnalysisRecord | null | undefined): OwnershipCandidate[] {
  return record?.candidates.filter(candidate => candidate.party.party_type === "NATURAL_PERSON"
    && candidate.synthetic_basis_threshold_result === "MET"
    && (candidate.classification === "REVIEW_REQUIRED" || candidate.classification === "INDETERMINATE")) ?? [];
}

// Named from the provenance of the links on the candidate's own retained paths.
export function assumedBasisLabel(record: OwnershipAnalysisRecord, candidate: OwnershipCandidate): string {
  const used = new Set(candidate.paths.flatMap(path => path.edges.map(edge => edge.relationship_id)));
  const providers = new Set(record.relationships.filter(edge => used.has(edge.relationship_id)).map(edge => edge.provenance.provider));
  if (providers.has("LOCAL_POC_ASSUMED_EQUAL_UNITS")) return "POC equal-unit assumption";
  if (providers.has("LOCAL_POC_ISSUED_CAPITAL_BASIS")) return "ACRA issued-capital POC basis";
  if (providers.has("LOCAL_SYNTHETIC_RELATIONSHIP")) return "Local synthetic overlay basis";
  return "Assumed POC basis";
}
