import { describe, expect, it } from "vitest";

import type { AuthenticatedProfile } from "../../types";
import { SAMPLE_CASES, sampleCaseDetail, sampleCaseRows } from "./onboardingSample";
import { sampleCaseSummary } from "./sampleCaseSummary";

const olivia = { user_id: "olivia-koh", display_name: "Olivia Koh", role: "DIRECTOR", team_id: null } as AuthenticatedProfile;
const AS_OF = Date.parse("2026-11-04T10:00:00Z");

function summaryFor(name: string) {
  const row = sampleCaseRows(olivia, AS_OF).find((item) => item.legal_name === name)!;
  return sampleCaseSummary(sampleCaseDetail(row.case_id, olivia, AS_OF)!);
}

describe("sample case summary for the case page", () => {
  it("gives every sample case the same twelve pipeline steps as a live case", () => {
    for (const row of sampleCaseRows(olivia, AS_OF)) {
      const summary = sampleCaseSummary(sampleCaseDetail(row.case_id, olivia, AS_OF)!);
      expect(summary.processing_pipeline).toHaveLength(12);
      expect(summary.case.case_id).toBe(row.case_id);
    }
    expect(sampleCaseRows(olivia, AS_OF)).toHaveLength(SAMPLE_CASES.length);
  });

  it("marks every step complete on a completed case, with no open blockers", () => {
    const summary = summaryFor("Raffles Row Partners Pte. Ltd.");
    expect(summary.processing_pipeline!.every((node) => node.status === "COMPLETE")).toBe(true);
    expect(summary.active_exceptions).toEqual([]);
  });

  it("stops an open case at its blocked step and leaves later steps not reached", () => {
    const summary = summaryFor("Sengkang Solar Installers Pte. Ltd.");
    const status = Object.fromEntries(summary.processing_pipeline!.map((node) => [node.node_id, node.status]));
    expect(status.DOCUMENT_IDP).toBe("COMPLETE");
    expect(status.OWNERSHIP_UBO).toBe("REVIEW_REQUIRED");
    expect(status.ADVISORY).toBe("NOT_REACHED");
    expect(status.FINAL_REVIEW_SEND).toBe("NOT_REACHED");
    expect(summary.active_exceptions.map((item) => [item.stage, item.status, item.blocker_code])).toEqual([["OWNERSHIP", "OPEN", "OWNERSHIP_INCOMPLETE"]]);
  });
});
