// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it } from "vitest";

import { governanceEventLabel, WorkflowHistory } from "./components/workflow-governance/WorkflowHistory";
import { governanceFixtures } from "./test-fixtures/workflowGovernance";
import type { WorkflowDetail } from "./workflowApi";
import type { GovernanceEvent, GovernanceEventKind } from "./workflowGovernanceTypes";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const event = (sequence: number, kind: GovernanceEventKind, overrides: Partial<GovernanceEvent> = {}): GovernanceEvent => ({
  sequence, occurred_at: `2026-11-${String(10 + sequence).padStart(2, "0")}T10:00:00Z`, actor_id: "hr-synthetic-1", kind,
  proposal_id: null, version: null, summary: "Server summary.", archived: false, ...overrides,
});
const LEGACY = [
  { occurred_at: "2026-11-01T10:00:00Z", actor_id: "director-legacy-1", action: "ACTIVATE", summary: "Activated version 1" },
  { occurred_at: "2026-11-02T10:00:00Z", actor_id: "director-legacy-1", action: "DRAFT", summary: "Saved draft" },
];

let root: Root | null = null;
let host: HTMLDivElement;
afterEach(() => { act(() => root?.unmount()); root = null; document.body.innerHTML = ""; });

function render(workflow: Pick<WorkflowDetail, "audit" | "governance">) {
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  act(() => root!.render(<WorkflowHistory workflow={workflow} />));
}
const governance = (recent_events: GovernanceEvent[]) => ({ ...governanceFixtures.workflowGovernanceView(), recent_events });

describe("Workflow History", () => {
  it("lists governance events newest first with plain labels, actor and time, then the legacy audit", () => {
    render({
      audit: LEGACY,
      governance: governance([
        event(1, "PROPOSAL_SUBMITTED"),
        event(3, "EMERGENCY_FALLBACK", { actor_id: "director-synthetic-1", version: 3 }),
        event(2, "VERSION_PUBLISHED", { actor_id: "director-synthetic-1", version: 2 }),
        event(4, "NOTICE_ACKNOWLEDGED"),
      ]),
    });
    const items = [...host.querySelectorAll('[data-testid="governance-events"] li')];
    expect(items.map(item => item.getAttribute("data-kind"))).toEqual(["NOTICE_ACKNOWLEDGED", "EMERGENCY_FALLBACK", "VERSION_PUBLISHED", "PROPOSAL_SUBMITTED"]);
    expect(items[0].textContent).toContain("Notice acknowledged · hr-synthetic-1 · ");
    expect(items[0].textContent).toContain(new Date("2026-11-14T10:00:00Z").toLocaleString());
    expect(items[1].textContent).toContain("Emergency fallback (not approved) · version 3 · director-synthetic-1");
    expect(items[1].textContent).not.toMatch(/approved by|approved ·|Approved/);
    expect(items[2].textContent).toContain("Version 2 published");
    expect(items[3].textContent).toContain("Proposal submitted");
    expect(host.textContent).not.toContain("No changes yet.");

    const legacy = host.querySelector('[data-testid="legacy-audit"]')!;
    expect(host.querySelector("#workflow-history-legacy")!.textContent).toBe("Before approval governance");
    const rows = [...legacy.querySelectorAll("li")];
    expect(rows.map(row => row.textContent)).toEqual([
      expect.stringContaining("Saved draft"), expect.stringContaining("Activated version 1"),
    ]);
    for (const row of rows) {
      expect(row.textContent).toContain("Before approval governance");
      expect(row.textContent).not.toMatch(/\bapproved\b/i);
    }
  });

  it("never words an emergency fallback or a legacy item as approved", () => {
    expect(governanceEventLabel(event(1, "EMERGENCY_FALLBACK"))).toBe("Emergency fallback (not approved)");
    expect(governanceEventLabel(event(1, "MIGRATED"))).not.toMatch(/approved/i);
    expect(governanceEventLabel(event(1, "PROPOSAL_APPROVED"))).toBe("Proposal approved by a Director");
  });

  it("shows the empty state only when both lists are empty", () => {
    render({ audit: [], governance: governance([]) });
    expect(host.textContent).toContain("No changes yet.");
    act(() => root?.unmount());
    document.body.innerHTML = "";

    render({ audit: LEGACY, governance: governance([]) });
    expect(host.textContent).not.toContain("No changes yet.");
    expect(host.querySelector('[data-testid="governance-events"]')).toBeNull();
    act(() => root?.unmount());
    document.body.innerHTML = "";

    render({ audit: [], governance: governance([event(1, "WORKFLOW_CREATED")]) });
    expect(host.textContent).not.toContain("No changes yet.");
    expect(host.querySelector('[data-testid="legacy-audit"]')).toBeNull();
  });

  it("keeps the existing audit list when governance is not migrated", () => {
    render({ audit: LEGACY, governance: null });
    expect(host.querySelector('[data-testid="governance-events"]')).toBeNull();
    expect(host.textContent).not.toContain("Before approval governance");
    expect([...host.querySelectorAll("li")].map(item => item.textContent)).toEqual([
      expect.stringContaining("Saved draft"), expect.stringContaining("Activated version 1"),
    ]);
    act(() => root?.unmount());
    document.body.innerHTML = "";
    render({ audit: [], governance: null });
    expect(host.textContent).toContain("No changes yet.");
  });
});
