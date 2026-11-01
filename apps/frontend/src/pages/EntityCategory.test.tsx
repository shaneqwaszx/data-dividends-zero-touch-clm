// @vitest-environment jsdom

import { act, type ComponentProps } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import { isRegistryIntakeUnavailable } from "../App";
import { createZeroTouchCase } from "../api";
import type { OnboardingCase, ZeroTouchCaseSummary } from "../types";
import HomeOnboarding from "./HomeOnboarding";
import IdentityCorrectionForm from "./IdentityCorrectionForm";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root | null = null;
let container: HTMLDivElement | null = null;

afterEach(() => {
  if (root) act(() => root?.unmount());
  container?.remove();
  root = null;
  container = null;
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function mount(element: React.ReactElement): HTMLDivElement {
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  act(() => root?.render(element));
  return container;
}

function choose(select: HTMLSelectElement, value: string): void {
  act(() => {
    Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")?.set?.call(select, value);
    select.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

function homeProps(overrides: Partial<ComponentProps<typeof HomeOnboarding>> = {}): ComponentProps<typeof HomeOnboarding> {
  return {
    summary: null, uen: "T99FY0105G", onUenChange: () => undefined, countryOfIncorporation: "SG",
    onCountryChange: () => undefined, documentFiles: [], onDocumentFilesChange: () => undefined,
    caseTeamDisplayName: "Alpha Corporate Onboarding", priority: "", onPriorityChange: () => undefined,
    isSubmitting: false, isResolving: false, requestError: null, pollingWarning: null, intakeProgress: null,
    onStart: () => undefined, onResolve: () => undefined, onReconcile: () => undefined,
    onReplace: () => undefined, onRecovery: () => undefined, onStartNewCase: () => undefined,
    onViewAudit: () => undefined, ...overrides,
  };
}

describe("D-114 entity type on Create case", () => {
  it("defaults to Company and reports the RM's choice", () => {
    const onEntityCategoryChange = vi.fn();
    const view = mount(<HomeOnboarding {...homeProps({ onEntityCategoryChange })} />);
    const select = view.querySelector<HTMLSelectElement>("#home-entity-category")!;
    expect(select.value).toBe("COMPANY");
    expect([...select.options].map((option) => option.textContent)).toEqual(["Company", "Partnership", "Government body"]);
    expect(view.querySelector("label[for='home-entity-category']")!.textContent).toBe("Entity type");
    expect(view.textContent).toContain("Government bodies are checked only in the government register, never ACRA.");
    choose(select, "GOVERNMENT");
    expect(onEntityCategoryChange).toHaveBeenCalledWith("GOVERNMENT");
  });

  it("sends entity_category only when one is chosen, so existing requests are unchanged", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({}), { status: 201, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    await createZeroTouchCase("209990101A", undefined, "SG", undefined, undefined, "DEMO ALPHA");
    await createZeroTouchCase("T99FY0105G", undefined, "SG", undefined, undefined, "DEMO PARKS", "GOVERNMENT");
    const bodies = fetchMock.mock.calls.map((call) => JSON.parse(String((call as unknown as [string, RequestInit])[1].body)));
    expect(bodies[0]).toEqual({ uen: "209990101A", country_of_incorporation: "SG", legal_name: "DEMO ALPHA" });
    expect(bodies[1]).toEqual({ uen: "T99FY0105G", country_of_incorporation: "SG", legal_name: "DEMO PARKS", entity_category: "GOVERNMENT" });
  });
});

describe("D-114 correction of the entity type", () => {
  const mismatch = {
    case_id: "case-1",
    requested_uen: "T99FY0105G",
    initial_identity: { legal_name: "DEMO PARKS FYP TEST AUTHORITY", registration_number: "T99FY0105G", country_of_incorporation: "SG" },
    error: { code: "ENTITY_CATEGORY_MISMATCH", message: "This UEN is a government body in the government register. Change the entity type to Government." },
  } as unknown as OnboardingCase;

  function renderCorrection(onboardingCase = mismatch) {
    const onSubmit = vi.fn();
    const view = mount(<IdentityCorrectionForm onboardingCase={onboardingCase} disabled={false} onSubmit={onSubmit} registryRecovery />);
    return { view, onSubmit };
  }

  it("shows the backend guidance and lets the RM change the entity type", () => {
    const { view, onSubmit } = renderCorrection();
    expect(view.textContent).toContain("Change the entity type to Government.");
    const edit = [...view.querySelectorAll("button")].find((item) => item.textContent === "Edit UEN or entity type")!;
    act(() => edit.click());
    const select = view.querySelector<HTMLSelectElement>("#identity-entity-category")!;
    expect(select.value).toBe("COMPANY");
    choose(select, "GOVERNMENT");
    act(() => view.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    expect(onSubmit).toHaveBeenCalledWith({
      legal_name: "DEMO PARKS FYP TEST AUTHORITY", registration_number: "T99FY0105G",
      country_of_incorporation: "SG", entity_category: "GOVERNMENT", choice: "OTHER",
    });
  });

  it("omits entity_category when the RM keeps the current type", () => {
    const government = { ...mismatch, initial_identity: { ...mismatch.initial_identity, entity_category: "GOVERNMENT" },
      error: { code: "GOVERNMENT_IDENTITY_NOT_FOUND", message: "No current government register record was found for this UEN. Check the UEN against the authority's letter, or change the entity type." } } as unknown as OnboardingCase;
    const { view, onSubmit } = renderCorrection(government);
    expect(view.textContent).toContain("Check the UEN against the authority's letter, or change the entity type.");
    act(() => [...view.querySelectorAll("button")].find((item) => item.textContent === "Edit UEN or entity type")!.click());
    expect(view.querySelector<HTMLSelectElement>("#identity-entity-category")!.value).toBe("GOVERNMENT");
    act(() => view.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    expect(onSubmit.mock.calls[0][0]).not.toHaveProperty("entity_category");
  });

  it("keeps the ordinary registry correction wording for other stops", () => {
    const { view } = renderCorrection({ ...mismatch, error: { code: "ACRA_ENTITY_NOT_FOUND", message: "No ACRA entity was found for this UEN." } } as unknown as OnboardingCase);
    expect([...view.querySelectorAll("button")].some((item) => item.textContent === "Edit UEN")).toBe(true);
    expect(view.textContent).not.toContain("No ACRA entity was found for this UEN.");
  });
});

describe("D-114 registry stops keep evidence intake open", () => {
  it.each(["GOVERNMENT_IDENTITY_NOT_FOUND", "ENTITY_CATEGORY_MISMATCH"])("%s", (code) => {
    const summary = {
      case: { jurisdiction_resolution: { status: "RESOLVED" }, registry_route: null, registry_acquisition: null },
      active_exceptions: [{ stage: "REGISTRY", blocker_code: code }],
    } as unknown as ZeroTouchCaseSummary;
    expect(isRegistryIntakeUnavailable(summary)).toBe(false);
  });
});
