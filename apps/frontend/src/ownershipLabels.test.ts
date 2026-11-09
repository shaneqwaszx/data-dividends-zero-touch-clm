import { describe, expect, it } from "vitest";

import {
  analysisStateText,
  calculationText,
  classificationText,
  comparatorSymbol,
  ownershipStatement,
  partyTypeText,
  thresholdResultText,
} from "./ownershipLabels";

const GTE = "GREATER_THAN_OR_EQUAL_TO";

describe("ownership labels", () => {
  it("describes every backend classification in plain language", () => {
    expect(classificationText("PROVISIONAL_UBO_CANDIDATE")).toBe("Provisional UBO candidate (meets the threshold; not verified)");
    expect(classificationText("BELOW_PROVISIONAL_THRESHOLD")).toBe("Below the threshold");
    expect(classificationText("REVIEW_REQUIRED")).toBe("Needs a person's review before any conclusion");
    expect(classificationText("INDETERMINATE")).toBe("Cannot be determined from the available records");
  });

  it("shows an unknown classification or result exactly as the backend sent it", () => {
    expect(classificationText("NEW_BACKEND_CLASSIFICATION")).toBe("NEW_BACKEND_CLASSIFICATION");
    expect(thresholdResultText("NEW_RESULT", "25", GTE)).toBe("NEW_RESULT");
    expect(thresholdResultText(null, "25", GTE)).toBe("Not available");
    expect(comparatorSymbol("SOME_OTHER_COMPARATOR")).toBe("SOME_OTHER_COMPARATOR");
  });

  it("describes the inclusive 25% threshold from the backend result", () => {
    expect(comparatorSymbol(GTE)).toBe("≥");
    expect(thresholdResultText("MET", "25.000000000000000000", GTE)).toBe("Meets the 25% threshold (25% or more)");
    expect(thresholdResultText("NOT_MET", "25.000000000000000000", GTE)).toBe("Below the 25% threshold");
    expect(thresholdResultText("INDETERMINATE", "25.000000000000000000", GTE)).toBe("Cannot be determined from the available records");
  });

  it("never recalculates the threshold: the wording follows the backend result, not the percentage", () => {
    // A holder of exactly 25% meets the inclusive threshold because the backend says MET.
    expect(thresholdResultText("MET", "25", GTE)).toContain("Meets");
    // 24.999999...% rounds to "25%" for display, but the backend result NOT_MET is what is shown.
    expect(thresholdResultText("NOT_MET", "25", GTE)).toBe("Below the 25% threshold");
    // The labels take no candidate percentage at all, so no client-side comparison is possible.
    expect(thresholdResultText.length).toBe(3);
  });

  it("states ownership owner first: the backend child holds a share of its parent", () => {
    expect(ownershipStatement("Jane Tan", "Alpha Pte Ltd", "60.000000000000000000")).toBe("Jane Tan owns 60% of Alpha Pte Ltd");
    expect(ownershipStatement("Holder", "Issuer", "0.000001")).toBe("Holder owns <0.01% of Issuer");
    expect(ownershipStatement("Holder", "Issuer", null)).toBe("Holder owns an unreported share of Issuer");
  });

  it("keeps the backend calculation, rounding percentages and using a multiplication sign", () => {
    expect(calculationText("50.000000% x 60.000000% = 30.000000%")).toBe("50% × 60% = 30%");
    expect(calculationText("100 × 100 / 100 = 100.000000000000000000")).toBe("100 × 100 / 100 = 100.000000000000000000");
    expect(calculationText("exact(1) = 0.00000000000000000001")).toBe("exact(1) = 0.00000000000000000001");
  });

  it("uses reader-facing party types and analysis states", () => {
    expect(partyTypeText("NATURAL_PERSON")).toBe("Individual");
    expect(partyTypeText("LEGAL_ENTITY")).toBe("Legal entity");
    expect(partyTypeText(undefined)).toBe("Unknown type");
    expect(analysisStateText("ANALYZED")).toBe("Calculated");
    expect(analysisStateText("REVIEW_REQUIRED")).toBe("Needs review");
    expect(analysisStateText("FAILED")).toBe("FAILED");
  });
});
