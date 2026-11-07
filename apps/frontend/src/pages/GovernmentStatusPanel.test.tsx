// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";

import { confirmGovernmentStatus } from "../api";
import type { EntityTypeBasis, GovernmentStatusProjection } from "../types";
import GovernmentStatusPanel from "./GovernmentStatusPanel";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const LABEL = "Local synthetic identity: not ACRA-registered; government status from reviewed document";

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

function basis(status: Partial<GovernmentStatusProjection>): EntityTypeBasis {
  return {
    entity_type: "GOVERNMENT",
    label: LABEL,
    government_status: {
      state: "CONFIRMATION_REQUIRED",
      document_id: "22222222-2222-4222-8222-222222222222",
      document_event_count: 4,
      founding_instrument: "Demo Parks FYP Test Authority Act (fictional FYP test instrument)",
      confirmed_by_actor_id: null,
      confirmed_at: null,
      ...status,
    },
  };
}

function render(value: EntityTypeBasis, { canConfirm = true, disabled = false, onConfirm = vi.fn(async () => false), onContinue = vi.fn() } = {}) {
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  act(() => root?.render(
    <GovernmentStatusPanel basis={value} canConfirm={canConfirm} disabled={disabled} onConfirm={onConfirm} onContinue={onContinue} />,
  ));
  return { view: container, onConfirm, onContinue };
}

const confirmButton = (view: HTMLElement) =>
  [...view.querySelectorAll("button")].find((button) => button.textContent === "Confirm Government status");

const input = (view: HTMLElement, name: string) => view.querySelector<HTMLInputElement>(`input[name="${name}"]`)!;
const radio = (view: HTMLElement, value: string) => view.querySelector<HTMLInputElement>(`input[type="radio"][value="${value}"]`)!;

/** Types like a user: React tracks the value through the native setter. */
function type(element: HTMLInputElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
  act(() => {
    setter.call(element, value);
    element.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function fillStatute(view: HTMLElement, statute = "Demo Parks FYP Test Authority Act", section = "", body = "STATUTORY_BOARD") {
  type(input(view, "founding_statute"), statute);
  if (section) type(input(view, "statute_section"), section);
  if (body) act(() => radio(view, body).click());
}

it("shows the server label and never claims ACRA verification", () => {
  const { view } = render(basis({}));
  expect(view.textContent).toContain(LABEL);
  expect(view.textContent).toContain("claims no ACRA verification");
  expect(view.textContent).not.toMatch(/ACRA[- ]verified/i);
  expect(view.textContent).toContain("Demo Parks FYP Test Authority Act");
  expect(view.textContent).toContain("not extracted, stored as an ownership graph or sent to GoldTier");
});

it("confirms only on an explicit click with the RM-entered statute, section and body type", async () => {
  const { view, onConfirm } = render(basis({}));
  expect(view.textContent).toContain("Founding instrument (from document)");
  expect(view.textContent).toContain("Type the Act that established this body, as shown on the status document (e.g. 'Demo Parks FYP Test Authority Act').");
  fillStatute(view, "  demo parks fyp test authority act  ", " s 3 ");
  expect(onConfirm).not.toHaveBeenCalled();
  await act(async () => confirmButton(view)!.click());
  expect(onConfirm).toHaveBeenCalledTimes(1);
  expect(onConfirm).toHaveBeenCalledWith({
    founding_statute: "demo parks fyp test authority act",
    statute_section: "s 3",
    government_body_type: "STATUTORY_BOARD",
  });
});

it("sends no section when it is left blank", async () => {
  const { view, onConfirm } = render(basis({}));
  fillStatute(view, "Demo Parks FYP Test Authority Act", "", "MINISTRY_OR_ORGAN_OF_STATE");
  await act(async () => confirmButton(view)!.click());
  expect(onConfirm).toHaveBeenCalledWith({
    founding_statute: "Demo Parks FYP Test Authority Act",
    statute_section: null,
    government_body_type: "MINISTRY_OR_ORGAN_OF_STATE",
  });
});

it("keeps the button disabled until the required fields are filled", () => {
  const { view } = render(basis({}));
  expect(confirmButton(view)!.disabled).toBe(true);
  expect(input(view, "founding_statute").maxLength).toBe(200);
  expect(input(view, "statute_section").maxLength).toBe(40);
  type(input(view, "founding_statute"), "Demo Parks FYP Test Authority Act");
  expect(confirmButton(view)!.disabled).toBe(true); // no body type yet
  act(() => radio(view, "STATUTORY_BOARD").click());
  expect(confirmButton(view)!.disabled).toBe(false);
  type(input(view, "founding_statute"), "  ab  "); // under 3 characters once trimmed
  expect(confirmButton(view)!.disabled).toBe(true);
  type(input(view, "founding_statute"), "   ");
  expect(confirmButton(view)!.disabled).toBe(true);
  type(input(view, "founding_statute"), "Act");
  expect(confirmButton(view)!.disabled).toBe(false);
  expect(view.textContent).toContain("Ministry or Organ of State");
  expect(view.textContent).toContain("Statutory Board");
});

it("shows the mismatch inline, keeps the inputs, and clears it when the statute is edited", async () => {
  const onConfirm = vi.fn(async () => true);
  const { view } = render(basis({}), { onConfirm });
  fillStatute(view, "Some Other Act", "s 3");
  await act(async () => confirmButton(view)!.click());
  const alert = view.querySelector('[role="alert"]');
  expect(alert?.textContent).toBe(
    "The statute you entered does not match the Founding Instrument on the reviewed document: \"Demo Parks FYP Test Authority Act (fictional FYP test instrument)\". Check the document, or upload a corrected status letter.",
  );
  expect(input(view, "founding_statute").value).toBe("Some Other Act");
  expect(input(view, "statute_section").value).toBe("s 3");
  expect(radio(view, "STATUTORY_BOARD").checked).toBe(true);
  expect(input(view, "founding_statute").getAttribute("aria-invalid")).toBe("true");
  type(input(view, "founding_statute"), "Demo Parks FYP Test Authority Act");
  expect(view.querySelector('[role="alert"]')).toBeNull();
});

it("shows no mismatch error for any other failure", async () => {
  const onConfirm = vi.fn(async () => false);
  const { view } = render(basis({}), { onConfirm });
  fillStatute(view);
  await act(async () => confirmButton(view)!.click());
  expect(view.querySelector('[role="alert"]')).toBeNull();
});

it("offers no confirmation without evidence, without permission, or once confirmed", () => {
  let { view } = render(basis({ state: "EVIDENCE_REQUIRED", document_id: null, document_event_count: null, founding_instrument: null }));
  expect(confirmButton(view)).toBeUndefined();
  expect(view.textContent).toContain("No current reviewed document shows every required label");
  act(() => root?.unmount()); container?.remove(); root = null;

  ({ view } = render(basis({}), { canConfirm: false }));
  expect(confirmButton(view)).toBeUndefined();
  expect(view.textContent).toContain("Only the case creator can confirm Government status.");
  act(() => root?.unmount()); container?.remove(); root = null;

  ({ view } = render(basis({ state: "CONFIRMED", confirmed_by_actor_id: "maya-lim", confirmed_at: "2026-10-29T08:00:00Z" })));
  expect(confirmButton(view)).toBeUndefined();
  expect(input(view, "founding_statute")).toBeNull();
  expect(view.textContent).toContain("maya-lim");
  expect(view.textContent).toContain("Government status confirmed from the reviewed document.");
});

it("shows what the RM entered once confirmed", () => {
  const rows = (view: HTMLElement) => Object.fromEntries(
    [...view.querySelectorAll("dt")].map((term) => [term.textContent, term.nextElementSibling?.textContent]),
  );
  let { view } = render(basis({
    state: "CONFIRMED", confirmed_by_actor_id: "maya-lim", confirmed_at: "2026-10-29T08:00:00Z",
    founding_statute: "demo parks fyp test authority act", statute_section: "s 3",
    government_body_type: "STATUTORY_BOARD", statute_match: "MATCHED_AFTER_NORMALISATION",
  }));
  expect(rows(view)).toMatchObject({
    "Founding instrument (from document)": "Demo Parks FYP Test Authority Act (fictional FYP test instrument)",
    "Founding statute (RM-entered)": "demo parks fyp test authority act",
    Section: "s 3",
    "Type of body": "Statutory Board",
    "Matched to document": "Yes",
    "Confirmed by": "maya-lim",
  });
  expect(rows(view)["Confirmed at"]).not.toBe("—");
  act(() => root?.unmount()); container?.remove(); root = null;

  ({ view } = render(basis({
    state: "CONFIRMED", confirmed_by_actor_id: "maya-lim", confirmed_at: "2026-10-29T08:00:00Z",
    founding_statute: "Demo Parks FYP Test Authority Act", statute_section: null,
    government_body_type: "MINISTRY_OR_ORGAN_OF_STATE", statute_match: "MATCHED_AFTER_NORMALISATION",
  })));
  expect(rows(view)).toMatchObject({ Section: "—", "Type of body": "Ministry or Organ of State" });
});

it("disables the form while another case action is in flight", () => {
  const { view } = render(basis({}), { disabled: true });
  expect(confirmButton(view)!.disabled).toBe(true);
  expect(input(view, "founding_statute").disabled).toBe(true);
});

it("posts the exact document version, revisions and the RM's statute to the confirmation route", async () => {
  const fetchMock = vi.fn(async () => new Response(JSON.stringify({}), { status: 200, headers: { "Content-Type": "application/json" } }));
  vi.stubGlobal("fetch", fetchMock);
  await confirmGovernmentStatus("case-1", {
    document_id: "22222222-2222-4222-8222-222222222222",
    document_event_count: 4,
    expected_automation_version: 7,
    expected_case_event_count: 12,
    founding_statute: "Demo Parks FYP Test Authority Act",
    statute_section: "s 3",
    government_body_type: "STATUTORY_BOARD",
  });
  const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
  expect(url).toContain("/api/clm/zero-touch/cases/case-1/government-status-confirmation");
  expect(init.method).toBe("POST");
  expect(JSON.parse(String(init.body))).toEqual({
    document_id: "22222222-2222-4222-8222-222222222222",
    document_event_count: 4,
    expected_automation_version: 7,
    expected_case_event_count: 12,
    founding_statute: "Demo Parks FYP Test Authority Act",
    statute_section: "s 3",
    government_body_type: "STATUTORY_BOARD",
  });
});

it("D-125: offers Continue onboarding instead of the form when the server says the step must reopen", () => {
  const { view, onConfirm, onContinue } = render(basis({ resume_required: true }));
  expect(view.querySelector('form[aria-label="Confirm Government status"]')).toBeNull();
  expect(confirmButton(view)).toBeUndefined();
  expect(view.textContent).toContain("confirmed before the founding statute was recorded");
  const resume = [...view.querySelectorAll("button")].find((button) => button.textContent === "Continue onboarding")!;
  expect(resume.disabled).toBe(false);
  act(() => resume.click());
  expect(onContinue).toHaveBeenCalledTimes(1);
  expect(onConfirm).not.toHaveBeenCalled();
});

it("D-125: Continue onboarding is disabled while busy and shown only to the case creator", () => {
  const busy = render(basis({ resume_required: true }), { disabled: true });
  expect([...busy.view.querySelectorAll("button")].find((button) => button.textContent === "Continue onboarding")!.disabled).toBe(true);
  act(() => root?.unmount()); root = null; container?.remove();
  const other = render(basis({ resume_required: true }), { canConfirm: false });
  expect(other.view.textContent).toContain("Only the case creator can confirm Government status.");
  expect([...other.view.querySelectorAll("button")].some((button) => button.textContent === "Continue onboarding")).toBe(false);
});

it("D-125: the form is shown when resume is not required", () => {
  const { view } = render(basis({ resume_required: false }));
  expect(view.querySelector('form[aria-label="Confirm Government status"]')).not.toBeNull();
  expect([...view.querySelectorAll("button")].some((button) => button.textContent === "Continue onboarding")).toBe(false);
});
