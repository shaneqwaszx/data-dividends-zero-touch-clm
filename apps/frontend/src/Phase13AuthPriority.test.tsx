import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { OperatorAccount } from "./App";
import {
  configureAuthenticatedTransport,
  createZeroTouchCase,
  fetchZeroTouchCases,
  login,
  logout,
  updateCasePriority,
} from "./api";
import { transitionAuthState, type AuthState } from "./auth";
import { loadCaseQueueRows } from "./pages/CaseQueue";
import { PriorityBadge, updatePriorityAndRefresh } from "./pages/PriorityControl";
import type { AuthSession, ZeroTouchCaseListItem, ZeroTouchCaseSummary } from "./types";
import { mapZeroTouchCaseToCaseRow } from "./viewModels";

const session: AuthSession = {
  profile: {
    user_id: "team-a-onboarder",
    display_name: "Team A Client Onboarder",
    role: "CLIENT_ONBOARDER",
    team_id: "TEAM_A",
    team_display_name: "Team A",
    client_scope_label: "DBS",
  },
  csrf_token: "opaque-csrf-token",
};

const anonymous: AuthState = { status: "anonymous", session: null, error: null };

function makeListItem(
  caseId: string,
  priority: number | null,
  updatedAt: string,
): ZeroTouchCaseListItem {
  return {
    case_id: caseId,
    team_id: "TEAM_A",
    client_scope_label: "DBS",
    priority,
    requested_uen: `20240000${caseId.at(-1)}A`,
    legal_name: `SYNTHETIC ${caseId.at(-1)}`,
    status: "RUNNING",
    current_stage: "REGISTRY",
    updated_at: updatedAt,
    active_exception_count: 0,
    human_interventions: 0,
    final_outcome: null,
  };
}

function makeDetail(caseId: string, caseUpdatedAt: string): ZeroTouchCaseSummary {
  return {
    case: {
      case_id: caseId,
      updated_at: caseUpdatedAt,
      jurisdiction_resolution: null,
    },
    created_at: "2026-09-07T00:00:00Z",
    updated_at: caseUpdatedAt,
  } as unknown as ZeroTouchCaseSummary;
}

function jsonResponse(value: unknown): Response {
  return new Response(JSON.stringify(value), { status: 200 });
}

afterEach(() => {
  configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: null });
  vi.unstubAllGlobals();
});

describe("Phase 13 authenticated frontend boundary", () => {
  it("models restore/login, expiry, and logout as explicit auth transitions", () => {
    const authenticated = transitionAuthState(anonymous, { type: "AUTHENTICATED", session });
    expect(authenticated).toEqual({ status: "authenticated", session, error: null });
    expect(transitionAuthState(authenticated, { type: "ANONYMOUS" })).toEqual(anonymous);
  });

  it("uses credentialed requests and sends CSRF only on unsafe methods", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        case_id: "00000000-0000-4000-8000-000000000001",
        team_id: "TEAM_A",
        priority: 10,
        updated_at: "2026-09-07T01:00:00Z",
      }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    configureAuthenticatedTransport({ csrfToken: session.csrf_token, onUnauthorized: null });

    await fetchZeroTouchCases();
    await updateCasePriority("00000000-0000-4000-8000-000000000001", 10);

    expect(fetchMock.mock.calls[0][1]).toMatchObject({ credentials: "include" });
    expect(new Headers(fetchMock.mock.calls[0][1].headers).has("X-CSRF-Token")).toBe(false);
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: "PATCH", credentials: "include" });
    expect(new Headers(fetchMock.mock.calls[1][1].headers).get("X-CSRF-Token")).toBe(session.csrf_token);
  });

  it("clears the sensitive UI state through the centralized 401 callback", async () => {
    const onUnauthorized = vi.fn();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: { code: "AUTHENTICATION_REQUIRED", message: "Authentication is required." } }), { status: 401 }),
    ));
    configureAuthenticatedTransport({ csrfToken: session.csrf_token, onUnauthorized });

    await expect(fetchZeroTouchCases()).rejects.toMatchObject({ status: 401 });
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });

  it("binds login, logout, and Director creation to the server contract", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(session), { status: 200 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({}), { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(login("team-a-onboarder", "runtime-only-password")).resolves.toEqual(session);
    configureAuthenticatedTransport({ csrfToken: session.csrf_token, onUnauthorized: null });
    await logout();
    await createZeroTouchCase("202400001A", undefined, "SG", "TEAM_B");

    expect(JSON.parse(fetchMock.mock.calls[0][1].body as string)).toEqual({
      user_id: "team-a-onboarder",
      "password": "runtime-only-password",
    });
    expect(new Headers(fetchMock.mock.calls[1][1].headers).get("X-CSRF-Token")).toBe(session.csrf_token);
    expect(JSON.parse(fetchMock.mock.calls[2][1].body as string)).toMatchObject({ team_id: "TEAM_B" });
  });

  it("renders only the server-returned profile and explicit priority states", () => {
    const account = renderToStaticMarkup(
      <OperatorAccount profile={session.profile} onLogout={() => undefined} />,
    );
    expect(account).toContain("Team A Client Onboarder");
    expect(account).toContain("Signed in as");
    expect(account).not.toContain("Demo operator");
    expect(renderToStaticMarkup(<PriorityBadge priority={10} />)).toContain("P10");
    expect(renderToStaticMarkup(<PriorityBadge priority={null} />)).toContain("Unprioritised");
  });

  it("preserves backend priority order while mapping rows", () => {
    const items = [10, 5, null].map((priority, index): ZeroTouchCaseListItem => ({
      case_id: `00000000-0000-4000-8000-00000000000${index + 1}`,
      team_id: "TEAM_A",
      client_scope_label: "DBS",
      priority,
      requested_uen: `20240000${index + 1}A`,
      legal_name: null,
      status: "RUNNING",
      current_stage: "REGISTRY",
      updated_at: "2026-09-07T01:00:00Z",
      active_exception_count: 0,
      human_interventions: 0,
      final_outcome: null,
    }));
    expect(items.map((item) => mapZeroTouchCaseToCaseRow(item).priority)).toEqual([10, 5, null]);
  });

  it("renders refetched server order and retains the list automation timestamp", async () => {
    const caseA = "00000000-0000-4000-8000-000000000001";
    const caseB = "00000000-0000-4000-8000-000000000002";
    const caseC = "00000000-0000-4000-8000-000000000003";
    const automationTimestamp = "2026-09-07T03:00:00Z";
    const caseMutationTimestamp = "2026-09-07T09:00:00Z";
    const initial = [
      makeListItem(caseA, 10, "2026-09-07T05:00:00Z"),
      makeListItem(caseB, 1, "2026-09-07T04:00:00Z"),
      makeListItem(caseC, null, automationTimestamp),
    ];
    const refetched = [
      initial[0],
      makeListItem(caseC, 9, automationTimestamp),
      initial[1],
    ];
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse(initial))
      .mockResolvedValueOnce(jsonResponse(makeDetail(caseA, "2026-09-07T05:00:00Z")))
      .mockResolvedValueOnce(jsonResponse(makeDetail(caseB, "2026-09-07T04:00:00Z")))
      .mockResolvedValueOnce(jsonResponse(makeDetail(caseC, "2026-09-07T02:00:00Z")))
      .mockResolvedValueOnce(jsonResponse({
        case_id: caseC,
        team_id: "TEAM_A",
        priority: 9,
        updated_at: caseMutationTimestamp,
      }))
      .mockResolvedValueOnce(jsonResponse(refetched))
      .mockResolvedValueOnce(jsonResponse(makeDetail(caseA, "2026-09-07T05:00:00Z")))
      .mockResolvedValueOnce(jsonResponse(makeDetail(caseC, caseMutationTimestamp)))
      .mockResolvedValueOnce(jsonResponse(makeDetail(caseB, "2026-09-07T04:00:00Z")));
    vi.stubGlobal("fetch", fetchMock);
    configureAuthenticatedTransport({ csrfToken: session.csrf_token, onUnauthorized: null });

    let refreshedRows = await loadCaseQueueRows();
    expect(refreshedRows.map((item) => item.case_id)).toEqual([
      caseA,
      caseB,
      caseC,
    ]);
    await updatePriorityAndRefresh(caseC, 9, async () => {
      refreshedRows = await loadCaseQueueRows();
    });
    const markup = renderToStaticMarkup(
      <ol>{refreshedRows.map((item) => <li key={item.case_id}>{item.case_id}</li>)}</ol>,
    );

    expect(refreshedRows.map((item) => item.case_id)).toEqual([caseA, caseC, caseB]);
    expect(markup.indexOf(caseA)).toBeLessThan(markup.indexOf(caseC));
    expect(markup.indexOf(caseC)).toBeLessThan(markup.indexOf(caseB));
    expect(refreshedRows[1].updated_at).toBe(automationTimestamp);
    expect(refreshedRows[1].updated_at).not.toBe(caseMutationTimestamp);
    expect(fetchMock.mock.calls.filter(([url]) => url === "/api/clm/zero-touch/cases"))
      .toHaveLength(2);
  });
});
