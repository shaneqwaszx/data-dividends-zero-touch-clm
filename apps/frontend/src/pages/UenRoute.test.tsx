// @vitest-environment jsdom

import { act, type ComponentProps } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { isRegistryIntakeUnavailable } from "../App";
import { createZeroTouchCase } from "../api";
import type { OnboardingCase, UenRouteDecision, ZeroTouchCaseSummary } from "../types";
import HomeOnboarding from "./HomeOnboarding";
import IdentityCorrectionForm from "./IdentityCorrectionForm";
import UenRouteNote from "./UenRouteNote";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root | null = null;
let container: HTMLDivElement | null = null;

afterEach(() => {
  if (root) act(() => root?.unmount());
  container?.remove();
  root = null;
  container = null;
  vi.unstubAllGlobals();
});

const GOVERNMENT_ROUTE: UenRouteDecision = {
  uen: "T99GB0105G", route: "GOVERNMENT_REGISTER", uen_format: "C", pq_code: "GB",
  entity_type: "statutory board", rule_version: "UEN-ROUTE-1",
  description: "Government body (statutory board, code GB) · checked against the government register, not ACRA",
};

describe("D-114 route from the UEN (read-only)", () => {
  it("shows the backend's recorded route as written", () => {
    const markup = renderToStaticMarkup(<UenRouteNote route={GOVERNMENT_ROUTE} />);
    expect(markup).toContain(
      "Entity type from UEN: Government body (statutory board, code GB) · checked against the government register, not ACRA",
    );
  });

  it("shows nothing before the backend has routed the UEN", () => {
    expect(renderToStaticMarkup(<UenRouteNote route={null} />)).toBe("");
    expect(renderToStaticMarkup(<UenRouteNote route={undefined} />)).toBe("");
  });
});

describe("D-114 Create case has no entity-type choice", () => {
  function homeProps(): ComponentProps<typeof HomeOnboarding> {
    return {
      summary: null, uen: "T99GB0105G", onUenChange: () => undefined, countryOfIncorporation: "SG",
      onCountryChange: () => undefined, documentFiles: [], onDocumentFilesChange: () => undefined,
      caseTeamDisplayName: "Alpha Corporate Onboarding", priority: "", onPriorityChange: () => undefined,
      isSubmitting: false, isResolving: false, requestError: null, pollingWarning: null, intakeProgress: null,
      onStart: () => undefined, onResolve: () => undefined, onReconcile: () => undefined,
      onReplace: () => undefined, onRecovery: () => undefined, onStartNewCase: () => undefined,
      onViewAudit: () => undefined,
    };
  }

  it("asks only for the UEN, name and country", () => {
    const markup = renderToStaticMarkup(<HomeOnboarding {...homeProps()} />);
    expect(markup).not.toContain("Entity type");
    expect(markup).toContain("Registration ID / UEN");
  });

  it("never sends an entity category", async () => {
    const fetchMock = vi.fn(async () => new Response("{}", { status: 201, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    await createZeroTouchCase("T99GB0105G", undefined, "SG", undefined, undefined, "DEMO PARKS FYP TEST AUTHORITY");
    const body = JSON.parse(String((fetchMock.mock.calls[0] as unknown as [string, RequestInit])[1].body));
    expect(body).toEqual({ uen: "T99GB0105G", country_of_incorporation: "SG", legal_name: "DEMO PARKS FYP TEST AUTHORITY" });
  });
});

describe("D-114 UEN-route stops", () => {
  const STOPS = [
    ["GOVERNMENT_IDENTITY_NOT_FOUND", "No current government register record was found for this UEN. Check the UEN against the authority's letter."],
    ["ENTITY_CATEGORY_MISMATCH", "This UEN has a government body record in the government register, but its format routes it to ACRA. Check the UEN; the case stays in review."],
    ["UEN_ENTITY_TYPE_UNSUPPORTED", "This UEN belongs to an entity type this POC doesn't onboard (society). Check the UEN."],
  ] as const;

  it.each(STOPS)("%s shows the backend guidance with the existing correct-UEN action", (code, message) => {
    const onboardingCase = {
      case_id: "case-1", requested_uen: "T09SS0001B",
      initial_identity: { legal_name: "DEMO", registration_number: "T09SS0001B", country_of_incorporation: "SG" },
      error: { code, message },
    } as unknown as OnboardingCase;
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
    act(() => root?.render(<IdentityCorrectionForm onboardingCase={onboardingCase} disabled={false} onSubmit={vi.fn()} registryRecovery />));
    expect(container.textContent).toContain(message);
    expect([...container.querySelectorAll("button")].some((item) => item.textContent === "Edit UEN")).toBe(true);
    expect(container.querySelector("select")).toBeNull();
  });

  it.each(STOPS.map(([code]) => code))("%s keeps evidence intake open", (code) => {
    const summary = {
      case: { jurisdiction_resolution: { status: "RESOLVED" }, registry_route: null, registry_acquisition: null },
      active_exceptions: [{ stage: "REGISTRY", blocker_code: code }],
    } as unknown as ZeroTouchCaseSummary;
    expect(isRegistryIntakeUnavailable(summary)).toBe(false);
  });
});
