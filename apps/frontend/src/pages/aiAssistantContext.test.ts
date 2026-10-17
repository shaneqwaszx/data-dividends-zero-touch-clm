import { describe, expect, it } from "vitest";

import { aiAssistantContextFor } from "./aiAssistantContext";

const ID = "3f89b02a-9a7d-4dac-906b-5df40fbdca34";
const OTHER = "00000000-0000-4000-8000-000000000002";

describe("aiAssistantContextFor", () => {
  it("uses the case on a case page under Cases", () => {
    expect(aiAssistantContextFor(`/cases/${ID}`, OTHER)).toEqual({ caseId: ID, onboardingWithoutCase: false });
  });

  it("uses the case being onboarded once it exists", () => {
    expect(aiAssistantContextFor("/new-onboarding", ID)).toEqual({ caseId: ID, onboardingWithoutCase: false });
    expect(aiAssistantContextFor(`/new-onboarding/${ID}`, null)).toEqual({ caseId: ID, onboardingWithoutCase: false });
  });

  it("asks for the company first on New onboarding before the case exists", () => {
    expect(aiAssistantContextFor("/new-onboarding", null)).toEqual({ caseId: null, onboardingWithoutCase: true });
  });

  it("has no case anywhere else", () => {
    for (const path of ["/", "/dashboard", "/cases", `/onboarded/${ID}`, `/audit/${ID}`, "/cases/not-a-case", `/cases/${ID}/x`]) {
      expect(aiAssistantContextFor(path, ID).caseId).toBeNull();
      expect(aiAssistantContextFor(path, ID).onboardingWithoutCase).toBe(false);
    }
  });
});
