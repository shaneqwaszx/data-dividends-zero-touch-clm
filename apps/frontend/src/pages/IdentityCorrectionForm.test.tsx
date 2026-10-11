// @vitest-environment jsdom

import { act, type ComponentProps } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";

import { recheckZeroTouchIdentitySearch } from "../api";
import { caseQueryKeys, identitySearchRecheckMutationEffect } from "../caseQueries";
import type { OnboardingCase, ZeroTouchCaseSummary } from "../types";
import IdentityCorrectionForm from "./IdentityCorrectionForm";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const onboardingCase = {
  case_id: "case-1",
  requested_uen: "202400001A",
  initial_identity: {
    legal_name: "Example Pte Ltd",
    registration_number: "202400001A",
    country_of_incorporation: "SG",
  },
} as unknown as OnboardingCase;

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

function render(onSubmit = vi.fn(), props: Partial<ComponentProps<typeof IdentityCorrectionForm>> = {}): { view: HTMLDivElement; onSubmit: ReturnType<typeof vi.fn> } {
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  act(() => root?.render(<IdentityCorrectionForm onboardingCase={onboardingCase} disabled={false} onSubmit={onSubmit} {...props} />));
  return { view: container, onSubmit };
}

function enter(input: HTMLInputElement, value: string): void {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
  setter?.call(input, value);
  input.dispatchEvent(new Event("input", { bubbles: true }));
}

describe("IdentityCorrectionForm", () => {
  it("distinguishes original and corrected Garden UEN and selects the current entered identity", () => {
    const { view, onSubmit } = render(vi.fn(), {
      registryRecovery: true,
      onboardingCase: {
        ...onboardingCase,
        requested_uen: "11111999A",
        initial_identity: { legal_name: "GARDEN BUSINESS", registration_number: "11111999A", country_of_incorporation: "SG" },
        identity_corrections: [{ previous_identity: { registration_number: "11111998B" }, corrected_identity: { registration_number: "11111999A" } }],
      } as unknown as OnboardingCase,
      documentCandidates: [{ uen: "11111997C", documentId: "garden-doc", eventCount: 8 }],
    });
    expect(view.textContent).toContain("Original entered UEN: 11111998B");
    expect(view.textContent).toContain("Current corrected UEN: 11111999A");
    expect(view.textContent).toContain("Document-detected UEN: 11111997C");
    act(() => Array.from(view.querySelectorAll("button")).find((item) => item.textContent === "Use entered UEN")!.click());
    expect(onSubmit).toHaveBeenLastCalledWith(expect.objectContaining({ registration_number: "11111999A", choice: "ENTERED" }));
  });
  it("rejects an invalid UEN inline without submitting an identity mutation", () => {
    const { view, onSubmit } = render();
    act(() => { enter(view.querySelector("#identity-registration-number") as HTMLInputElement, "NOT-A-UEN"); });
    act(() => { view.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })); });
    expect(view.querySelector('[role="alert"]')?.textContent).toContain("Singapore UEN");
    expect(onSubmit).not.toHaveBeenCalled();
  });
  it("exposes all bounded identity choices with selected document version", () => {
    const { view, onSubmit } = render(vi.fn(), {
      registryRecovery: true,
      documentCandidates: [{ uen: "202400009I", documentId: "synthetic-doc", eventCount: 8 }],
    });
    const button = (label: string) => Array.from(view.querySelectorAll("button")).find(
      (item) => item.textContent === label,
    )!;
    expect(view.textContent).toContain("Entity identity requires confirmation");
    act(() => button("Use entered UEN").click());
    expect(onSubmit).toHaveBeenLastCalledWith(expect.objectContaining({
      registration_number: "202400001A", choice: "ENTERED",
    }));
    act(() => button("Use document UEN").click());
    expect(onSubmit).toHaveBeenLastCalledWith(expect.objectContaining({
      registration_number: "202400009I", choice: "DOCUMENT",
      document_id: "synthetic-doc", expected_document_event_count: 8,
    }));
    act(() => button("Enter another UEN").click());
    expect(view.querySelector("#identity-registration-number")).not.toBeNull();
  });
  it("collects legal name and UEN, fixes country to SG, and states the evidence boundary", () => {
    const { view } = render();
    expect((view.querySelector("#identity-legal-name") as HTMLInputElement).value).toBe("Example Pte Ltd");
    expect((view.querySelector("#identity-registration-number") as HTMLInputElement).value).toBe("202400001A");
    const country = view.querySelector("#identity-country") as HTMLInputElement;
    expect(country.value).toBe("SG");
    expect(country.readOnly).toBe(true);
    expect(view.textContent).toContain("not authoritative registry evidence");
    expect(view.textContent).toContain("read-only GoldTier Search");
  });

  it("normalizes entered values and submits no inferred authority", () => {
    const { view, onSubmit } = render();
    const name = view.querySelector("#identity-legal-name") as HTMLInputElement;
    const uen = view.querySelector("#identity-registration-number") as HTMLInputElement;
    act(() => {
      enter(name, "  Corrected Company Pte Ltd  ");
      enter(uen, "202499999z");
    });
    act(() => {
      view.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });
    expect(onSubmit).toHaveBeenCalledWith({
      legal_name: "Corrected Company Pte Ltd",
      registration_number: "202499999Z",
      country_of_incorporation: "SG",
    });
  });
});

describe("identity Search recheck integration", () => {
  it("posts one exact CAS-bound request to the same-case recheck endpoint", async () => {
    const summary = { case: { case_id: "case-1" } } as ZeroTouchCaseSummary;
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(summary), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    const payload = {
      legal_name: "Corrected Company Pte Ltd",
      registration_number: "202499999Z",
      country_of_incorporation: "SG" as const,
      expected_automation_version: 8,
      expected_clm_version: 4,
      expected_case_event_count: 6,
    };

    await recheckZeroTouchIdentitySearch("case-1", payload);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/api/clm/zero-touch/cases/case-1/identity-search-recheck");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual(payload);
  });

  it("publishes and invalidates only the acting user's case scopes", () => {
    const client = new QueryClient();
    const summary = { case: { case_id: "case-1" } } as ZeroTouchCaseSummary;
    client.setQueryData(caseQueryKeys.detail("other-user", "case-1"), { marker: "untouched" });
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const remove = vi.spyOn(client, "removeQueries");

    identitySearchRecheckMutationEffect(client, "case-user", summary);

    expect(client.getQueryData(caseQueryKeys.detail("case-user", "case-1"))).toBe(summary);
    expect(client.getQueryData(caseQueryKeys.detail("other-user", "case-1"))).toEqual({ marker: "untouched" });
    expect(invalidate.mock.calls.every(([filters]) => JSON.stringify(filters?.queryKey).includes("case-user"))).toBe(true);
    expect(remove.mock.calls.every(([filters]) => JSON.stringify(filters?.queryKey).includes("case-user"))).toBe(true);
  });
});
