// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ZeroTouchCaseSummary } from "../types";
import CaseStateExplanationPanel from "./CaseStateExplanationPanel";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function summary(): ZeroTouchCaseSummary {
  return {
    status: "WAITING_FOR_REVIEW", current_stage: "DOCUMENT",
    clm: { readiness: { registry: { status: "READY" }, document: { status: "REVIEW_REQUIRED" }, ownership: { status: "BLOCKED" }, goldtier: { status: "NOT_SUBMITTED" }, blockers: ["Exact blocker <unsafe>"], warnings: ["Exact warning & retained"] } },
    active_exceptions: [{ exception_id: "exception-1", stage: "DOCUMENT", blocker_code: "DOCUMENT_SOURCE_CONFLICT", explanation: "Exact retained explanation.", blocker_codes: [], evidence: [], available_actions: [], status: "OPEN" }],
    target_operations: [{ operation: "SEARCH", status: "NO_MATCH" }, { operation: "SHELL", status: "CREATED" }, { operation: "POLICY", status: "NOT_ATTEMPTED" }],
    technical_failure: { code: "CLM_TARGET_OUTCOME_UNCERTAIN", message: "Sanitized technical failure." },
  } as unknown as ZeroTouchCaseSummary;
}

let root: Root | null = null; let container: HTMLDivElement | null = null;
afterEach(() => { if (root) act(() => root?.unmount()); container?.remove(); root = null; container = null; });
function render(value: ZeroTouchCaseSummary, onNavigate = vi.fn()) { container = document.createElement("div"); document.body.append(container); root = createRoot(container); act(() => root?.render(<CaseStateExplanationPanel summary={value} onNavigate={onNavigate} />)); return { view: container, onNavigate }; }
function click(text: string) { const button = [...container!.querySelectorAll("button")].find((item) => item.textContent === text)!; expect(button).toBeTruthy(); act(() => button.click()); }

describe("CaseStateExplanationPanel", () => {
  it("renders status, stage readiness, blockers and warnings verbatim and safely", () => {
    const { view } = render(summary()); const text = view.textContent ?? "";
    expect(text).toContain("WAITING_FOR_REVIEW — The workflow is waiting for human review."); expect(text).toContain("DOCUMENT — Document evidence and reconciliation stage");
    expect(text).toContain("RegistryREADY"); expect(text).toContain("DocumentREVIEW_REQUIRED"); expect(text).toContain("OwnershipBLOCKED"); expect(text).toContain("GoldTierNOT_SUBMITTED");
    expect(text).toContain("Exact blocker <unsafe>"); expect(text).toContain("Exact warning & retained"); expect(view.querySelector("unsafe")).toBeNull();
    expect(text).toContain("DOCUMENT · DOCUMENT_SOURCE_CONFLICT"); expect(text).toContain("Exact retained explanation.");
  });

  it("preserves supplied target operation order and does not reinterpret absence", () => {
    const { view } = render(summary()); const operations = [...view.querySelectorAll('[aria-label="Target operations"] li')].map((item) => item.textContent);
    expect(operations).toEqual(["SEARCH: NO_MATCH", "SHELL: CREATED", "POLICY: NOT_ATTEMPTED"]); expect(view.textContent).toContain("Mock target success is not customer, compliance, legal, or Ready-for-Approval approval");
    act(() => root?.render(<CaseStateExplanationPanel summary={{ ...summary(), target_operations: [] }} onNavigate={() => undefined} />));
    expect(view.textContent).toContain("Their absence does not mean success, skipped, or retryable");
  });

  it("uses only fixed stage/code navigation callbacks", () => {
    const { onNavigate } = render(summary());
    click("Focus registry evidence"); click("Focus documents evidence"); click("Focus evidence for DOCUMENT_SOURCE_CONFLICT"); click("Focus recovery evidence");
    expect(onNavigate.mock.calls).toEqual([["registry"], ["documents"], ["reconciliation"], ["recovery"]]);
  });

  it("uses visible uncertainty fallbacks for unknown runtime values", () => {
    const unknown = {
      ...summary(),
      status: "FUTURE_STATE",
      current_stage: "FUTURE_STAGE",
      clm: {
        ...summary().clm,
        readiness: {
          ...summary().clm.readiness,
          registry: { status: "FUTURE_READINESS" },
        },
      },
      active_exceptions: [{ ...summary().active_exceptions[0], stage: "FUTURE_STAGE", blocker_code: "FUTURE_CODE" }],
      target_operations: [{ operation: "FUTURE_OPERATION", status: "FUTURE_TARGET_STATUS" }],
    } as unknown as ZeroTouchCaseSummary;
    const { view } = render(unknown); expect(view.textContent).toContain("Unknown automation state value “FUTURE_STATE”; no interpretation is available."); expect(view.textContent).toContain("Unknown automation stage value “FUTURE_STAGE”; no interpretation is available."); expect(view.textContent).toContain("No fixed evidence destination is available");
    expect(view.textContent).toContain("Unknown readiness status “FUTURE_READINESS”; no interpretation is available.");
    expect(view.textContent).toContain("Unknown target operation “FUTURE_OPERATION”; no interpretation is available.");
    expect(view.textContent).toContain("Unknown target operation status “FUTURE_TARGET_STATUS”; no interpretation is available.");
  });

  it("is prop-only and exposes no action forms or links", () => {
    const { view } = render(summary()); expect(view.querySelector("form")).toBeNull(); expect(view.querySelector("a")).toBeNull(); expect(view.querySelector("input, select, textarea")).toBeNull();
  });
});
