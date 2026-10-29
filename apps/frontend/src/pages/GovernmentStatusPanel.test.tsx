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

function render(value: EntityTypeBasis, { canConfirm = true, disabled = false, onConfirm = vi.fn() } = {}) {
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  act(() => root?.render(
    <GovernmentStatusPanel basis={value} canConfirm={canConfirm} disabled={disabled} onConfirm={onConfirm} />,
  ));
  return { view: container, onConfirm };
}

const confirmButton = (view: HTMLElement) =>
  [...view.querySelectorAll("button")].find((button) => button.textContent === "Confirm Government status");

it("shows the server label and never claims ACRA verification", () => {
  const { view } = render(basis({}));
  expect(view.textContent).toContain(LABEL);
  expect(view.textContent).toContain("claims no ACRA verification");
  expect(view.textContent).not.toMatch(/ACRA[- ]verified/i);
  expect(view.textContent).toContain("Demo Parks FYP Test Authority Act");
  expect(view.textContent).toContain("not extracted, stored as an ownership graph or sent to GoldTier");
});

it("confirms only on an explicit click and only when the server allows it", () => {
  const { view, onConfirm } = render(basis({}));
  expect(onConfirm).not.toHaveBeenCalled();
  act(() => confirmButton(view)!.click());
  expect(onConfirm).toHaveBeenCalledTimes(1);
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
  expect(view.textContent).toContain("maya-lim");
  expect(view.textContent).toContain("Government status confirmed from the reviewed document.");
});

it("disables the button while another case action is in flight", () => {
  const { view } = render(basis({}), { disabled: true });
  expect(confirmButton(view)!.disabled).toBe(true);
});

it("posts the exact document version and revisions to the confirmation route", async () => {
  const fetchMock = vi.fn(async () => new Response(JSON.stringify({}), { status: 200, headers: { "Content-Type": "application/json" } }));
  vi.stubGlobal("fetch", fetchMock);
  await confirmGovernmentStatus("case-1", {
    document_id: "22222222-2222-4222-8222-222222222222",
    document_event_count: 4,
    expected_automation_version: 7,
    expected_case_event_count: 12,
  });
  const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
  expect(url).toContain("/api/clm/zero-touch/cases/case-1/government-status-confirmation");
  expect(init.method).toBe("POST");
  expect(JSON.parse(String(init.body))).toEqual({
    document_id: "22222222-2222-4222-8222-222222222222",
    document_event_count: 4,
    expected_automation_version: 7,
    expected_case_event_count: 12,
  });
});
