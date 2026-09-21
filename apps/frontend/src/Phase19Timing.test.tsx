// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { casePortfolioQueryOptions } from "./caseQueries";
import CaseQueue, { DEFAULT_CASE_QUEUE_PRESENTATION } from "./pages/CaseQueue";
import { OperationalTiming } from "./pages/CaseStatePanels";
import { createSessionQueryClient } from "./queryClient";
import { formatDuration } from "./shared";
import type {
  AuthenticatedProfile,
  CasePortfolioItem,
  ZeroTouchCaseSummary,
} from "./types";

const actor: AuthenticatedProfile = {
  user_id: "ethan-tan",
  display_name: "Ethan Tan",
  role: "RELATIONSHIP_MANAGER",
  team_id: "TEAM_A",
  team_display_name: "Alpha",
  team_type: "Corporate Client Onboarding",
  team_description: "Synthetic team",
  client_scope_label: "Alpha",
  capabilities: ["CASE_ACCESS"],
};

function item(completed: boolean): CasePortfolioItem {
  return {
    case_id: completed
      ? "00000000-0000-4000-8000-000000000192"
      : "00000000-0000-4000-8000-000000000191",
    team_id: "TEAM_A",
    client_scope_label: "Alpha",
    priority: 8,
    requested_uen: completed ? "202400002A" : "202400001A",
    legal_name: completed ? "COMPLETED TIMING PTE. LTD." : "ACTIVE TIMING PTE. LTD.",
    status: completed ? "COMPLETED" : "RUNNING",
    current_stage: completed ? "COMPLETE" : "DOCUMENT",
    updated_at: "2026-09-21T10:00:00Z",
    active_exception_count: 0,
    active_exception_types: [],
    human_interventions: 0,
    final_outcome: completed ? "MOCK_GOLDTIER_SUBMITTED" : null,
    resolved_jurisdiction: "SG",
    created_at: "2026-09-21T08:00:00Z",
    completed_at: completed ? "2026-09-21T08:00:41Z" : null,
    mock_goldtier_party_id: completed ? "GT-MOCK-1" : null,
    timing: {
      case_elapsed_ms: completed ? 41_000 : 11_640_000,
      time_since_last_update_ms: 1_680_000,
      automation_elapsed_ms: completed ? 12_000 : null,
      recorded_total_duration_ms: completed ? 12_000 : null,
    },
  };
}

let root: Root | null = null;
let container: HTMLDivElement | null = null;

beforeEach(() => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean })
    .IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
});

afterEach(async () => {
  if (root) await act(async () => root?.unmount());
  container?.remove();
  root = null;
  container = null;
});

describe("Phase 19 factual timing", () => {
  it.each([
    [0, "< 1s"],
    [999, "< 1s"],
    [1_000, "1s"],
    [12_000, "12s"],
    [252_000, "4m 12s"],
    [11_640_000, "3h 14m"],
    [190_800_000, "2d 5h"],
  ])("formats %i exact milliseconds as %s", (milliseconds, expected) => {
    expect(formatDuration(milliseconds)).toBe(expected);
  });

  it("renders neutral active/completed facts from one cached server observation", async () => {
    const queryClient = createSessionQueryClient();
    const query = casePortfolioQueryOptions(actor.user_id, {
      priority: "all",
      prioritySort: "highest_first",
      teamFilter: "all",
      offset: 0,
      limit: 50,
    });
    queryClient.setQueryData(query.queryKey, {
      observed_at: "2026-09-21T12:00:00Z",
      items: [item(false), item(true)],
      offset: 0,
      limit: 50,
      has_more: false,
    });

    await act(async () => root?.render(
      <MemoryRouter><QueryClientProvider client={queryClient}>
        <CaseQueue
          actor={actor}
          presentation={DEFAULT_CASE_QUEUE_PRESENTATION}
          onPresentationChange={() => undefined}
        />
      </QueryClientProvider></MemoryRouter>,
    ));

    expect(container?.textContent).toContain("Timing observed at");
    expect(container?.textContent).toContain("Refresh to obtain a new observation");
    expect(container?.textContent).toContain("Case age: 3h 14m");
    expect(container?.textContent).toContain("Case duration: 41s");
    expect(container?.textContent).toContain("Last updated: 28m ago");
    expect(container?.textContent).not.toMatch(/\b(?:overdue|late|breach|healthy|on time|SLA)\b/i);
  });

  it("updates only when a refreshed response supplies a new observation", async () => {
    const queryClient = createSessionQueryClient();
    const query = casePortfolioQueryOptions(actor.user_id, {
      priority: "all",
      prioritySort: "highest_first",
      teamFilter: "all",
      offset: 0,
      limit: 50,
    });
    const first = item(false);
    queryClient.setQueryData(query.queryKey, {
      observed_at: "2026-09-21T12:00:00Z",
      items: [first],
      offset: 0,
      limit: 50,
      has_more: false,
    });
    await act(async () => root?.render(
      <MemoryRouter><QueryClientProvider client={queryClient}>
        <CaseQueue actor={actor} presentation={DEFAULT_CASE_QUEUE_PRESENTATION} onPresentationChange={() => undefined} />
      </QueryClientProvider></MemoryRouter>,
    ));
    expect(container?.textContent).toContain("Case age: 3h 14m");

    await act(async () => {
      queryClient.setQueryData(query.queryKey, {
        observed_at: "2026-09-21T13:00:00Z",
        items: [{
          ...first,
          timing: {
            ...first.timing,
            case_elapsed_ms: 15_240_000,
            time_since_last_update_ms: 5_280_000,
          },
        }],
        offset: 0,
        limit: 50,
        has_more: false,
      });
    });
    await act(async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 0));
    });
    expect(queryClient.getQueryData(query.queryKey)).toMatchObject({
      observed_at: "2026-09-21T13:00:00Z",
    });
    expect(container?.textContent).toContain("Case age: 4h 14m");
    expect(container?.textContent).toContain("Last updated: 1h 28m ago");
  });

  it("labels detailed stage values as recorded automated processing only", async () => {
    const summary = {
      status: "COMPLETED",
      timing: {
        observed_at: "2026-09-21T12:00:00Z",
        case_elapsed_ms: 41_000,
        time_since_last_update_ms: 7_200_000,
        automation_elapsed_ms: 12_000,
        recorded_total_duration_ms: 12_000,
      },
      metrics: {
        total_duration_ms: 12_000,
        stage_durations_ms: { DOCUMENT: 4_200 },
      },
    } as unknown as ZeroTouchCaseSummary;

    await act(async () => root?.render(<OperationalTiming summary={summary} />));

    expect(container?.textContent).toContain("Operational timing");
    expect(container?.textContent).toContain("Case duration");
    expect(container?.textContent).toContain("Recorded total automation duration");
    expect(container?.textContent).toContain("Recorded automated-stage processing duration");
    expect(container?.textContent).toContain("completed automated processing attempts only");
    expect(container?.textContent).toContain("do not represent human waiting time");
  });
});
