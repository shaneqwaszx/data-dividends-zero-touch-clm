// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { expect, it } from "vitest";

import type { ZeroTouchCaseSummary } from "../types";
import { OnboardingProgressPanel } from "./CaseStatePanels";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

it("keeps stage details under the progress boxes collapsed until the user opens them", async () => {
  const summary = {
    case: { case_id: "00000000-0000-4000-8000-000000000001", requested_uen: "11111999A" },
    clm: { submission_plan: { environment: "MOCK" } },
    status: "WAITING_FOR_REVIEW",
    current_stage: "DOCUMENT",
    active_exceptions: [],
    interventions: [],
    processing_pipeline: [{ node_id: "DOCUMENT_IDP", label: "Document verification", status: "REVIEW_REQUIRED", children: [], safe_result: "Fields need review" }],
    updated_at: "2026-10-21T15:56:13Z",
  } as unknown as ZeroTouchCaseSummary;
  const host = document.createElement("div"); document.body.append(host);
  const root = createRoot(host);
  await act(async () => root.render(<OnboardingProgressPanel summary={summary} />));
  await act(async () => host.querySelector<HTMLButtonElement>('button[aria-label="Open details for Document verification"]')!.click());
  const details = host.querySelector<HTMLDetailsElement>("details#processing-stage-details")!;
  expect(details).not.toBeNull();
  expect(details.open).toBe(false);
  expect(details.querySelector("summary")!.textContent).toBe("Stage details — Document verification");
  expect(details.textContent).toContain("Fields need review");
  await act(async () => root.unmount()); host.remove();
});
