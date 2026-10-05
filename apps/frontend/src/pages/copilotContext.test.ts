import { describe, expect, it } from "vitest";

import { copilotContextFor } from "./copilotContext";

const ID = "3f89b02a-9a7d-4dac-906b-5df40fbdca34";
const OTHER = "00000000-0000-4000-8000-000000000002";

describe("copilotContextFor", () => {
  it("uses the case on a case page under Cases", () => {
    expect(copilotContextFor(`/cases/${ID}`, OTHER)).toEqual({ caseId: ID, onboardingWithoutCase: false });
  });

  it("uses the case being onboarded once it exists", () => {
    expect(copilotContextFor("/new-onboarding", ID)).toEqual({ caseId: ID, onboardingWithoutCase: false });
    expect(copilotContextFor(`/new-onboarding/${ID}`, null)).toEqual({ caseId: ID, onboardingWithoutCase: false });
  });

  it("asks for the company first on New onboarding before the case exists", () => {
    expect(copilotContextFor("/new-onboarding", null)).toEqual({ caseId: null, onboardingWithoutCase: true });
  });

  it("has no case anywhere else", () => {
    for (const path of ["/", "/dashboard", "/cases", `/onboarded/${ID}`, `/audit/${ID}`, "/cases/not-a-case", `/cases/${ID}/x`]) {
      expect(copilotContextFor(path, ID).caseId).toBeNull();
      expect(copilotContextFor(path, ID).onboardingWithoutCase).toBe(false);
    }
  });
});
