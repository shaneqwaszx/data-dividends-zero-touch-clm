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
import { AuthProvider, transitionAuthState, type AuthState } from "./auth";
import { loadCaseQueueRows } from "./pages/CaseQueue";
import LoginPage from "./pages/LoginPage";
import HomeOnboarding, { openCaseDetailAtStage } from "./pages/HomeOnboarding";
import {
  PriorityBadge,
  default as PriorityControl,
  PriorityListControls,
  updatePriorityAndRefresh,
} from "./pages/PriorityControl";
import type { AuthenticatedProfile, AuthSession, ZeroTouchCaseListItem, ZeroTouchCaseSummary } from "./types";
import { mapZeroTouchCaseToCaseRow } from "./viewModels";

const session: AuthSession = {
  profile: {
    user_id: "maya-lim",
    display_name: "Maya Lim",
    role: "CLIENT_ONBOARDER",
    team_id: "TEAM_A",
    team_display_name: "DBS Corporate Onboarding",
    team_type: "Corporate Client Onboarding",
    team_description: "Type: Corporate Client Onboarding | Client coverage: DBS",
    client_scope_label: "DBS",
    capabilities: ["POLICY_VIEW", "CASE_ACCESS"],
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
    active_exception_types: [],
    human_interventions: 0,
    final_outcome: null,
    resolved_jurisdiction: "SG",
    created_at: updatedAt,
    completed_at: null,
    mock_goldtier_party_id: null,
  };
}

function makeDetail(caseId: string, caseUpdatedAt: string): ZeroTouchCaseSummary {
  return {
    case: {
      case_id: caseId,
      requested_uen: "202400001A",
      priority: null,
      updated_at: caseUpdatedAt,
      jurisdiction_resolution: null,
    },
    status: "PENDING_INPUTS",
    current_stage: "DOCUMENT",
    completed_stages: ["REGISTRY"],
    active_exceptions: [],
    technical_failure: null,
    reconciliation: null,
    timeline: [],
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
  it("preserves a selected retained-case pipeline node when opening Case Detail", () => {
    const open = vi.fn();
    openCaseDetailAtStage(open, "case-1", {
      node_id: "GOLDTIER_SEARCH",
      label: "GoldTier search",
      status: "FAILED",
      children: [],
    });

    expect(open).toHaveBeenCalledWith("case-1", "GOLDTIER_SEARCH");
  });

  it("renders the canonical team and complete optional priority choices", () => {
    const markup = renderToStaticMarkup(
      <HomeOnboarding
        summary={null}
        uen="202400001A"
        onUenChange={() => undefined}
        countryOfIncorporation="SG"
        onCountryChange={() => undefined}
        documentFiles={[]}
        onDocumentFilesChange={() => undefined}
        caseTeamDisplayName="DBS Corporate Onboarding"
        priority=""
        onPriorityChange={() => undefined}
        isSubmitting={false}
        isResolving={false}
        requestError={null}
        pollingWarning={null}
        intakeProgress={null}
        onStart={() => undefined}
        onResolve={() => undefined}
        onReconcile={() => undefined}
        onReplace={() => undefined}
        onRecovery={() => undefined}
        onStartNewCase={() => undefined}
        onViewOnboarded={() => undefined}
        onViewAudit={() => undefined}
      />,
    );

    expect(markup).toContain("Case priority");
    expect(markup).toContain("Optional ordering label only");
    expect(markup).toContain('value="" selected=""');
    expect(markup).toContain(">Low</option>");
    expect(markup).toContain(">Medium</option>");
    expect(markup).toContain(">High</option>");
    expect(markup).not.toContain("10 — Highest");
    expect(markup).toContain("DBS Corporate Onboarding");
    expect(markup).not.toContain("Create case for team");
  });

  it("disables creation when an explicit Director team has not been selected", () => {
    const markup = renderToStaticMarkup(
      <HomeOnboarding
        summary={null}
        uen="202400001A"
        onUenChange={() => undefined}
        legalName="Synthetic Company"
        countryOfIncorporation="SG"
        onCountryChange={() => undefined}
        documentFiles={[]}
        onDocumentFilesChange={() => undefined}
        caseTeamDisplayName="Select a team above"
        priority=""
        onPriorityChange={() => undefined}
        isSubmitting={false}
        isResolving={false}
        creationDisabled
        requestError={null}
        pollingWarning={null}
        intakeProgress={null}
        onStart={() => undefined}
        onResolve={() => undefined}
        onReconcile={() => undefined}
        onReplace={() => undefined}
        onRecovery={() => undefined}
        onStartNewCase={() => undefined}
        onViewOnboarded={() => undefined}
        onViewAudit={() => undefined}
      />,
    );

    expect(markup).toContain('type="submit"');
    expect(markup).toContain('disabled=""');
    expect(markup).toContain("Select a team above");
  });

  it("shows retained-case open and delete controls only when deletion is authorized", () => {
    const created = makeDetail("00000000-0000-4000-8000-000000000001", "2026-09-07T01:00:00Z");
    const common = {
      summary: created,
      uen: "202400001A",
      onUenChange: () => undefined,
      countryOfIncorporation: "SG" as const,
      onCountryChange: () => undefined,
      documentFiles: [],
      onDocumentFilesChange: () => undefined,
      caseTeamDisplayName: "DBS Corporate Onboarding",
      priority: "" as const,
      onPriorityChange: () => undefined,
      isSubmitting: false,
      isResolving: false,
      requestError: null,
      pollingWarning: null,
      intakeProgress: null,
      onStart: () => undefined,
      onResolve: () => undefined,
      onReconcile: () => undefined,
      onReplace: () => undefined,
      onRecovery: () => undefined,
      onStartNewCase: () => undefined,
      onViewOnboarded: () => undefined,
      onViewAudit: () => undefined,
    };

    const allowed = renderToStaticMarkup(<HomeOnboarding {...common} canDeleteCurrentCase />);
    const hidden = renderToStaticMarkup(<HomeOnboarding {...common} />);
    expect(allowed).toContain("Open full case");
    expect(allowed).toContain("Delete case");
    expect(hidden).toContain("Open full case");
    expect(hidden).not.toContain("Delete case");
  });

  it("sends priority in the one create request and omits it when unset", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse({}))
      .mockResolvedValueOnce(jsonResponse({}))
      .mockResolvedValueOnce(jsonResponse({}));
    vi.stubGlobal("fetch", fetchMock);

    await createZeroTouchCase("202400001A", undefined, "SG", undefined, 7);
    await createZeroTouchCase("202400002B", undefined, "SG", undefined, null);
    await createZeroTouchCase("202400007G", undefined, "SG", "TEAM_B", 10);

    expect(JSON.parse(fetchMock.mock.calls[0][1].body as string)).toEqual({
      uen: "202400001A",
      country_of_incorporation: "SG",
      priority: 7,
    });
    expect(JSON.parse(fetchMock.mock.calls[1][1].body as string)).toEqual({
      uen: "202400002B",
      country_of_incorporation: "SG",
    });
    expect(JSON.parse(fetchMock.mock.calls[2][1].body as string)).toMatchObject({
      team_id: "TEAM_B",
      priority: 10,
    });
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("shows the selected priority from the returned created case", () => {
    const created = makeDetail("00000000-0000-4000-8000-000000000001", "2026-09-07T01:00:00Z");
    created.case.priority = 7;
    const markup = renderToStaticMarkup(
      <HomeOnboarding
        summary={created}
        uen="202400001A"
        onUenChange={() => undefined}
        countryOfIncorporation="SG"
        onCountryChange={() => undefined}
        documentFiles={[]}
        onDocumentFilesChange={() => undefined}
        caseTeamDisplayName="DBS Corporate Onboarding"
        priority={7}
        onPriorityChange={() => undefined}
        isSubmitting={false}
        isResolving={false}
        requestError={null}
        pollingWarning={null}
        intakeProgress={null}
        onStart={() => undefined}
        onResolve={() => undefined}
        onReconcile={() => undefined}
        onReplace={() => undefined}
        onRecovery={() => undefined}
        onStartNewCase={() => undefined}
        onViewOnboarded={() => undefined}
        onViewAudit={() => undefined}
      />,
    );

    expect(markup).toContain("Medium");
  });

  it("keeps unsupported assignment and generic rework out of operational exception actions", () => {
    const created = makeDetail("00000000-0000-4000-8000-000000000001", "2026-09-07T01:00:00Z");
    created.status = "WAITING_FOR_REVIEW";
    created.active_exceptions = [{
      exception_id: "00000000-0000-4000-8000-000000000099",
      case_id: created.case.case_id,
      exception_type: "DOCUMENT_SOURCE_CONFLICT",
      stage: "DOCUMENT",
      status: "OPEN",
      blocker_code: "DOCUMENT_SOURCE_CONFLICT",
      blocker_codes: ["DOCUMENT_SOURCE_CONFLICT"],
      explanation: "Document evidence needs a bounded decision.",
      evidence: [],
      available_actions: ["KEEP_REGISTRY_VALUE"],
      evidence_version: "evidence-v1",
      automation_version: 1,
      created_at: "2026-09-07T01:00:00Z",
      resolved_at: null,
      resolution: null,
    }] as ZeroTouchCaseSummary["active_exceptions"];
    created.interventions = [{
      intervention_id: "00000000-0000-4000-8000-000000000099",
      owning_stage: "DOCUMENT",
      owning_stage_label: "Documents / reconciliation",
      title: "Document or reconciliation review required",
      blocker_code: "DOCUMENT_SOURCE_CONFLICT",
      explanation: "Document evidence needs a bounded decision.",
      required_evidence_or_input: ["Current document evidence."],
      authorized_actions: [{
        action: "KEEP_REGISTRY_VALUE",
        label: "Keep registry value",
        description: "Retain the current registry observation.",
      }],
      no_action_reason: null,
      expected_next_step: "The owning service will re-evaluate retained evidence.",
      candidate_summaries: [],
    }];

    const markup = renderToStaticMarkup(
      <HomeOnboarding
        summary={created}
        uen="202400001A"
        onUenChange={() => undefined}
        countryOfIncorporation="SG"
        onCountryChange={() => undefined}
        documentFiles={[]}
        onDocumentFilesChange={() => undefined}
        caseTeamDisplayName="DBS Corporate Onboarding"
        priority=""
        onPriorityChange={() => undefined}
        isSubmitting={false}
        isResolving={false}
        requestError={null}
        pollingWarning={null}
        intakeProgress={null}
        onStart={() => undefined}
        onResolve={() => undefined}
        onReconcile={() => undefined}
        onReplace={() => undefined}
        onRecovery={() => undefined}
        onStartNewCase={() => undefined}
        onViewOnboarded={() => undefined}
        onViewAudit={() => undefined}
      />,
    );

    expect(markup).toContain("Keep registry value");
    expect(markup).not.toMatch(/Assign reviewer|Return for rework/);
  });

  it("does not consult browser storage as an authorization owner", async () => {
    const storage = { getItem: vi.fn(), setItem: vi.fn(), removeItem: vi.fn(), clear: vi.fn() };
    vi.stubGlobal("localStorage", storage);
    vi.stubGlobal("sessionStorage", storage);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse([])));

    await fetchZeroTouchCases();

    expect(storage.getItem).not.toHaveBeenCalled();
    expect(storage.setItem).not.toHaveBeenCalled();
  });

  it("sends typed priority filter and sort parameters to the backend", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([]));
    vi.stubGlobal("fetch", fetchMock);

    await fetchZeroTouchCases("COMPLETED", "unset", "lowest_first");

    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/clm/zero-touch/cases?status=COMPLETED&priority_filter=unset&priority_sort=lowest_first",
    );
  });

  it("renders complete priority filtering and sorting controls", () => {
    const markup = renderToStaticMarkup(
      <PriorityListControls
        filter="all"
        sort="highest_first"
        onFilterChange={() => undefined}
        onSortChange={() => undefined}
      />,
    );

    expect(markup).toContain("Priority: All");
    expect(markup).toContain("Prioritised only");
    expect(markup).toContain("Unprioritised only");
    expect(markup).not.toContain("Priority 10");
    expect(markup).not.toContain("Priority 1");
    expect(markup).toContain("Highest priority first");
    expect(markup).toContain("Lowest priority first");
  });

  it("offers only tier write values while safely presenting legacy stored priorities", () => {
    const markup = renderToStaticMarkup(
      <PriorityControl priority={7} onSave={async () => undefined} />,
    );
    expect(markup).toContain('<option value="1">Low</option>');
    expect(markup).toContain('<option value="5" selected="">Medium</option>');
    expect(markup).toContain('<option value="10">High</option>');
    expect(markup).not.toMatch(/>2<|>3<|>4<|>6<|>7<|>8<|>9</);
  });
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

    await expect(login("maya-lim", "runtime-only-password")).resolves.toEqual(session);
    configureAuthenticatedTransport({ csrfToken: session.csrf_token, onUnauthorized: null });
    await logout();
    await createZeroTouchCase("202400001A", undefined, "SG", "TEAM_B");

    expect(JSON.parse(fetchMock.mock.calls[0][1].body as string)).toEqual({
      user_id: "maya-lim",
      "password": "runtime-only-password",
    });
    expect(new Headers(fetchMock.mock.calls[1][1].headers).get("X-CSRF-Token")).toBe(session.csrf_token);
    expect(JSON.parse(fetchMock.mock.calls[2][1].body as string)).toMatchObject({ team_id: "TEAM_B" });
  });

  it("renders only the server-returned profile and explicit priority states", () => {
    const account = renderToStaticMarkup(
      <OperatorAccount profile={session.profile} onLogout={() => undefined} />,
    );
    expect(account).toContain("Maya Lim");
    expect(account).toContain("DBS Corporate Onboarding");
    expect(account).toContain("Coverage: DBS");
    expect(account).toContain("Signed in as");
    expect(account).not.toContain("Demo operator");
    expect(renderToStaticMarkup(<PriorityBadge priority={10} />)).toContain("High");
    expect(renderToStaticMarkup(<PriorityBadge priority={null} />)).toContain("Unprioritised");
  });

  it("presents person-like login IDs and Director global scope without a password hint", () => {
    const loginMarkup = renderToStaticMarkup(<AuthProvider><LoginPage /></AuthProvider>);
    const director: AuthenticatedProfile = {
      user_id: "olivia-koh",
      display_name: "Olivia Koh",
      role: "DIRECTOR" as const,
      team_id: null,
      team_display_name: null,
      team_type: null,
      team_description: "Global / cross-team access",
      client_scope_label: "Global / cross-team",
      capabilities: ["POLICY_VIEW", "POLICY_MUTATE", "CASE_ACCESS", "CASE_GLOBAL"],
    };
    const account = renderToStaticMarkup(
      <OperatorAccount profile={director} onLogout={() => undefined} />,
    );

    expect(loginMarkup).toContain('placeholder="maya-lim"');
    expect(loginMarkup).not.toContain("runtime-only-password");
    expect(account).toContain("Olivia Koh");
    expect(account).toContain("Global scope");
    expect(account).toContain("Global / cross-team access");
    expect(account).not.toContain("Team A");
    expect(account).not.toContain("Team B");
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
      active_exception_types: [],
      human_interventions: 0,
      final_outcome: null,
      resolved_jurisdiction: "SG",
      created_at: "2026-09-07T00:00:00Z",
      completed_at: null,
      mock_goldtier_party_id: null,
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
      .mockResolvedValueOnce(jsonResponse({
        case_id: caseC,
        team_id: "TEAM_A",
        priority: 9,
        updated_at: caseMutationTimestamp,
      }))
      .mockResolvedValueOnce(jsonResponse(refetched));
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
