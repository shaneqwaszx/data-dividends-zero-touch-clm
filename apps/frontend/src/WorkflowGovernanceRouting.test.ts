import { describe, expect, it } from "vitest";
import { hasCapability, paths, requiredCapabilityForPath, WORKFLOW_EDITOR_CAPABILITIES } from "./navigation";
import type { Capability } from "./types";

// Mirrors ROLE_CAPABILITIES in apps/backend/app/domain/access.py (policy and workflow capabilities only).
// The backend remains authoritative; this checks the UI never offers these pages to other roles.
const ROLE_POLICY_CAPABILITIES: Record<string, Capability[]> = {
  CLIENT_ONBOARDER: ["POLICY_VIEW", "CASE_ACCESS"],
  RELATIONSHIP_MANAGER: ["POLICY_VIEW", "CASE_ACCESS"],
  DIRECTOR: ["POLICY_VIEW", "POLICY_APPROVE", "CASE_ACCESS"],
  HR: ["POLICY_VIEW", "POLICY_MUTATE"],
  SUPPORT: ["POLICY_VIEW"],
};

const can = (role: string, path: string) => {
  const required = requiredCapabilityForPath(path);
  return required !== null && hasCapability(ROLE_POLICY_CAPABILITIES[role], required);
};

describe("workflow governance routing (QG P1)", () => {
  it("lets exactly HR and Directors reach the Workflows editor", () => {
    expect(WORKFLOW_EDITOR_CAPABILITIES).toEqual(["POLICY_MUTATE", "POLICY_APPROVE"]);
    expect(Object.keys(ROLE_POLICY_CAPABILITIES).filter((role) => can(role, paths.workflows))).toEqual([
      "DIRECTOR",
      "HR",
    ]);
  });

  it("keeps approvals and the comparison for Directors only", () => {
    const compare = paths.workflowCompare("corporate-onboarding", "0b6f7c2e-1d3a-4c5b-9e8f-7a6b5c4d3e2f");
    for (const path of [paths.workflowApprovals, compare]) {
      expect(Object.keys(ROLE_POLICY_CAPABILITIES).filter((role) => can(role, path))).toEqual(["DIRECTOR"]);
    }
  });

  it("evaluates single and any-of requirements", () => {
    expect(hasCapability(["CASE_ACCESS"], "CASE_ACCESS")).toBe(true);
    expect(hasCapability(["CASE_ACCESS"], "POLICY_VIEW")).toBe(false);
    expect(hasCapability(["POLICY_MUTATE"], WORKFLOW_EDITOR_CAPABILITIES)).toBe(true);
    expect(hasCapability(["POLICY_VIEW"], WORKFLOW_EDITOR_CAPABILITIES)).toBe(false);
    expect(hasCapability([], [])).toBe(false);
  });
});
