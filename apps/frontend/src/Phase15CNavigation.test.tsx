// @vitest-environment jsdom

import { act, StrictMode, type ReactNode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import {
  Link,
  MemoryRouter,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
} from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import {
  configureAuthenticatedTransport,
  fetchDashboard,
  fetchZeroTouchCase,
  fetchZeroTouchCases,
} from "./api";
import { AuthProvider, useAuth } from "./auth";
import {
  caseDeletedEffect,
  caseDetailQueryOptions,
  caseQueryKeys,
  documentQueryOptions,
  ownershipQueryOptions,
} from "./caseQueries";
import {
  defaultPathForProfile,
  paths,
  requiredCapabilityForPath,
  routePatterns,
  WorkspaceRoutes,
  WorkspaceTabs,
} from "./navigation";
import AuditTrail from "./pages/AuditTrail";
import CaseDetail from "./pages/CaseDetail";
import CaseQueue, { DEFAULT_CASE_QUEUE_PRESENTATION } from "./pages/CaseQueue";
import LoginPage from "./pages/LoginPage";
import OnboardedClients from "./pages/OnboardedClients";
import RetainedIntakeRecovery from "./pages/RetainedIntakeRecovery";
import { clearSessionQueries, createSessionQueryClient } from "./queryClient";
import type {
  AuthenticatedProfile,
  AuthSession,
  DocumentProcessingRecord,
  ZeroTouchCaseListItem,
  ZeroTouchCaseSummary,
  ZeroTouchException,
} from "./types";

const CASE_A = "00000000-0000-4000-8000-00000000015a";
const CASE_B = "00000000-0000-4000-8000-00000000015b";
const NOW = "2026-09-19T01:00:00Z";

const actor: AuthenticatedProfile = {
  user_id: "maya-lim",
  display_name: "Maya Lim",
  role: "CLIENT_ONBOARDER",
  team_id: "TEAM_A",
  team_display_name: "DBS Corporate Onboarding",
  team_type: "Corporate Client Onboarding",
  team_description: "Synthetic team",
  client_scope_label: "DBS",
  capabilities: ["CASE_ACCESS", "POLICY_VIEW"],
};

const allCapabilitiesActor: AuthenticatedProfile = {
  ...actor,
  user_id: "olivia-koh",
  display_name: "Olivia Koh",
  role: "DIRECTOR",
  team_id: null,
  team_display_name: null,
  team_type: null,
  team_description: "Global synthetic scope",
  client_scope_label: "Global / cross-team",
  capabilities: [
    "CASE_ACCESS",
    "CASE_GLOBAL",
    "POLICY_VIEW",
    "POLICY_MUTATE",
    "IDENTITY_ADMIN",
    "TEAM_ADMIN",
  ],
};

const hrActor: AuthenticatedProfile = {
  ...actor,
  user_id: "harper-lee",
  display_name: "Harper Lee",
  role: "HR",
  capabilities: ["IDENTITY_ADMIN", "PROVIDER_SANDBOX_TEST"],
};

const relationshipActor: AuthenticatedProfile = {
  ...actor,
  user_id: "rachel-tan",
  display_name: "Rachel Tan",
  role: "RELATIONSHIP_MANAGER",
};

const replacementActor: AuthenticatedProfile = {
  ...actor,
  user_id: "second-user",
  display_name: "Second User",
};

const session: AuthSession = { profile: actor, csrf_token: "synthetic-csrf" };

const listItem: ZeroTouchCaseListItem = {
  case_id: CASE_A,
  team_id: "TEAM_A",
  client_scope_label: "DBS",
  priority: 5,
  requested_uen: "202400001A",
  legal_name: "SYNTHETIC NAVIGATION PTE. LTD.",
  status: "PENDING_INPUTS",
  current_stage: "DOCUMENT",
  updated_at: NOW,
  active_exception_count: 0,
  active_exception_types: [],
  human_interventions: 0,
  final_outcome: null,
  resolved_jurisdiction: "SG",
  created_at: NOW,
  completed_at: null,
  mock_goldtier_party_id: null,
};

function summaryFixture(caseId: string, label = "SYNTHETIC CASE"): ZeroTouchCaseSummary {
  return {
    case: {
      case_id: caseId,
      requested_uen: label,
      priority: 5,
      client_scope_label: "DBS",
      created_by_actor_id: actor.user_id,
      events: [{ sequence: 1, event_type: "CASE_CREATED", timestamp: NOW }],
    },
    evidence_decision_authorized: true,
    ownership_edit_authorized: false,
    status: "PENDING_INPUTS",
    current_stage: "DOCUMENT",
    completed_stages: ["REGISTRY"],
    active_exceptions: [],
    technical_failure: null,
    reconciliation: null,
    target_operations: [],
    timeline: [],
    timing: {
      observed_at: NOW,
      case_elapsed_ms: 0,
      time_since_last_update_ms: 0,
      automation_elapsed_ms: null,
      recorded_total_duration_ms: null,
    },
    created_at: NOW,
    updated_at: NOW,
  } as unknown as ZeroTouchCaseSummary;
}

function documentFixture(caseId: string): DocumentProcessingRecord {
  return {
    case_id: caseId,
    document_id: "00000000-0000-4000-8000-000000000150",
    correlation_id: "synthetic-correlation",
    display_name: "retained-package.pdf",
    media_type: "application/pdf",
    size_bytes: 7,
    profile: "PROVISIONAL_CORPORATE",
    provider_environment: "LOCAL",
    state: "REVIEW_REQUIRED",
    review_source_fingerprint: "a".repeat(64),
    fields: [{
      field_key: "legal_name",
      original_extracted_value: "SYNTHETIC CASE",
      normalized_value: "SYNTHETIC CASE",
      confidence: 0.97,
      provenance: { provider: "LOCAL_PDF_TEXT", environment: "LOCAL", page_number: 1, source_reference: "safe:navigation" },
      canonical_value: "SYNTHETIC CASE",
      comparison_status: "MATCH",
      review_status: "PENDING",
      reviewed_value: null,
      reviewed_at: null,
      review_note: null,
    }],
    events: [],
    error: null,
    created_at: NOW,
    processed_at: NOW,
    reviewed_at: null,
    updated_at: NOW,
    supersedes_document_id: null,
    superseded_by_document_id: null,
  } as DocumentProcessingRecord;
}


async function acceptDraftControl(): Promise<HTMLButtonElement> {
  const control = container!.querySelector<HTMLInputElement>('input[data-review-field="legal_name"][value="ACCEPTED"]');
  if (control && !control.disabled) await act(async () => control.click());
  return Array.from(container!.querySelectorAll<HTMLButtonElement>("button"))
    .find(button => button.textContent === "Confirm decisions & continue onboarding")!;
}

function json(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function unavailable(status = 404): Response {
  return json({ detail: { code: "CASE_NOT_FOUND", message: "The case is unavailable." } }, status);
}

function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function caseDetailFixture(caseId: string, label: string): ZeroTouchCaseSummary {
  const exception: ZeroTouchException = {
    exception_id: `${caseId.slice(0, -1)}e`,
    exception_type: "DOCUMENT_REVIEW_REQUIRED",
    stage: "DOCUMENT",
    explanation: `${label} requires an explicit action.`,
    evidence: [],
    available_actions: ["REQUEST_ADDITIONAL_INFORMATION"],
    evidence_version: 1,
    created_at: NOW,
  } as unknown as ZeroTouchException;
  return {
    case: {
      case_id: caseId,
      requested_uen: label,
      priority: 5,
      client_scope_label: "DBS",
      entity: { legal_name: label },
      jurisdiction_resolution: null,
      registry_acquisition: null,
      goldtier_result: null,
      created_by_actor_id: relationshipActor.user_id,
      events: [{ sequence: 1, event_type: "CASE_CREATED", timestamp: NOW }],
    },
    evidence_decision_authorized: true,
    ownership_edit_authorized: false,
    version: 1,
    status: "WAITING_FOR_REVIEW",
    current_stage: "DOCUMENT",
    completed_stages: ["REGISTRY"],
    active_exceptions: [exception],
    technical_failure: null,
    reconciliation: null,
    metrics: {
      automated_stages_completed: 1,
      human_interventions: 0,
      exceptions_raised: 1,
      exceptions_resolved: 0,
      final_outcome: null,
      total_duration_ms: null,
      stage_durations_ms: {},
    },
    clm: {
      readiness: {
        registry: { status: "READY" },
        document: { status: "BLOCKED" },
        ownership: { status: "BLOCKED" },
        goldtier: { status: "BLOCKED" },
        blockers: [],
        warnings: [],
      },
      submission_plan: {
        environment: "MOCK",
        base_operations: [],
        real_ready_for_approval: "NOT_AVAILABLE",
      },
    },
    target_operations: [],
    timeline: [],
    timing: {
      observed_at: NOW,
      case_elapsed_ms: 0,
      time_since_last_update_ms: 0,
      automation_elapsed_ms: null,
      recorded_total_duration_ms: null,
    },
    created_at: NOW,
    updated_at: NOW,
  } as unknown as ZeroTouchCaseSummary;
}

function seedCaseDetail(queryClient: QueryClient, caseId: string, label: string) {
  queryClient.setQueryData(caseQueryKeys.detail(relationshipActor.user_id, caseId), caseDetailFixture(caseId, label));
  queryClient.setQueryData(caseQueryKeys.documents(relationshipActor.user_id, caseId), [documentFixture(caseId)]);
  queryClient.setQueryData(caseQueryKeys.ownership(relationshipActor.user_id, caseId), null);
  queryClient.setQueryData(caseQueryKeys.intelligence(relationshipActor.user_id, caseId), null);
}

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname}</output>;
}

function Screen({ children }: { children: ReactNode }) {
  return <h1 data-testid="screen">{children}</h1>;
}

function RouteFixture({ profile = allCapabilitiesActor }: { profile?: AuthenticatedProfile }) {
  return (
    <>
      <WorkspaceTabs actor={profile} retainedIntakeCaseId={null} />
      <WorkspaceRoutes
        actor={profile}
        retainedIntakeCaseId={null}
        dashboard={<Screen>dashboard</Screen>}
        newOnboarding={(caseId) => <Screen>{caseId ? `intake:${caseId}` : "new-onboarding"}</Screen>}
        cases={<Screen>cases</Screen>}
        caseDetail={(caseId) => <Screen>{`case:${caseId}`}</Screen>}
        onboarded={<Screen>onboarded</Screen>}
        onboardedDetail={(caseId) => <Screen>{`client:${caseId}`}</Screen>}
        audit={(caseId) => <><Screen>{caseId ? `audit:${caseId}` : "audit"}</Screen>{caseId && <Link to={paths.audit}>Clear case filter</Link>}</>}
        policy={<Screen>policy</Screen>}
        adminUsers={<Screen>users</Screen>}
        adminTeams={<Screen>teams</Screen>}
        goldtierSandbox={<Screen>goldtier-sandbox</Screen>}
        acraDiagnostics={<Screen>acra-diagnostics</Screen>}
      />
      <LocationProbe />
    </>
  );
}

function RoutedCaseDetail({ onBack }: { onBack: () => void }) {
  const caseId = useParams().caseId!;
  const navigate = useNavigate();
  return (
    <CaseDetail
      caseId={caseId}
      actor={relationshipActor}
      onBack={() => { onBack(); navigate(paths.cases); }}
      onViewOnboarded={(id) => navigate(paths.onboardedDetail(id))}
      onViewAudit={(id) => navigate(paths.auditCase(id))}
    />
  );
}

function CaseDetailRouteHarness({ onBack }: { onBack: () => void }) {
  const navigate = useNavigate();
  return (
    <>
      <nav>
        <Link to={paths.caseDetail(CASE_A)}>Open A</Link>
        <Link to={paths.caseDetail(CASE_B)}>Open B</Link>
        <button type="button" onClick={() => navigate(-1)}>History back</button>
        <button type="button" onClick={() => navigate(1)}>History forward</button>
      </nav>
      <Routes>
        <Route path={routePatterns.caseDetail} element={<RoutedCaseDetail onBack={onBack} />} />
        <Route path={routePatterns.cases} element={<Screen>cases</Screen>} />
      </Routes>
      <LocationProbe />
    </>
  );
}

function AuthenticatedAppBoundary() {
  const auth = useAuth();
  if (auth.status === "loading") return <p>restoring</p>;
  if (auth.status === "anonymous" || !auth.session) return <LoginPage />;
  return (
    <App
      key={auth.session.profile.user_id}
      actor={auth.session.profile}
      onLogout={() => void auth.logout()}
    />
  );
}

function IntakeRaceHarness({ profile = actor }: { profile?: AuthenticatedProfile }) {
  return (
    <>
      <Link data-testid="newer-journey" to={paths.retainedIntake(CASE_B)}>Open newer journey</Link>
      <App key={profile.user_id} actor={profile} onLogout={() => undefined} />
      <LocationProbe />
    </>
  );
}

function testClient(): QueryClient {
  return new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 60_000 } } });
}

async function selectIntakeFileAndSubmit(fileName = "race-package.pdf") {
  const uenInput = container?.querySelector<HTMLInputElement>("#home-uen");
  const nameInput = container?.querySelector<HTMLInputElement>("#home-legal-name");
  const setValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
  await act(async () => {
    for (const [input, value] of [[uenInput, "202400001A"], [nameInput, "SYNTHETIC NAVIGATION PTE. LTD."]] as const) {
      if (!input) continue;
      setValue.call(input, value);
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }
  });
  const file = new File(["synthetic"], fileName, { type: "application/pdf", lastModified: 1 });
  const fileInput = Array.from(container?.querySelectorAll<HTMLInputElement>("input[type='file']") ?? [])
    .find((input) => !input.hasAttribute("webkitdirectory"));
  Object.defineProperty(fileInput, "files", { configurable: true, value: [file] });
  await act(async () => fileInput?.dispatchEvent(new Event("change", { bubbles: true })));
  await act(async () => container?.querySelector<HTMLFormElement>("form")?.dispatchEvent(
    new Event("submit", { bubbles: true, cancelable: true }),
  ));
}

async function startFreshFromNewerJourney() {
  await act(async () => container?.querySelector<HTMLAnchorElement>("[data-testid='newer-journey']")?.click());
  await vi.waitFor(() => expect(container?.textContent).toContain("Continue from retained backend state"));
  const startFresh = Array.from(container?.querySelectorAll<HTMLButtonElement>("button") ?? [])
    .find((button) => button.textContent === "Start a fresh case");
  await act(async () => startFresh?.click());
  expect(container?.querySelector("[data-testid='location']")?.textContent).toBe(paths.newOnboarding);
}

async function logoutAndLoginAsReplacement() {
  await act(async () => container?.querySelector<HTMLButtonElement>(".operator-account__button")?.click());
  const signOut = Array.from(container?.querySelectorAll<HTMLButtonElement>("button") ?? [])
    .find((button) => button.textContent === "Sign out");
  await act(async () => signOut?.click());
  await vi.waitFor(() => expect(container?.textContent).toContain("Sign in"));
  const inputs = container?.querySelectorAll<HTMLInputElement>("input");
  await act(async () => {
    if (inputs?.[0]) {
      inputs[0].value = replacementActor.user_id;
      inputs[0].dispatchEvent(new Event("input", { bubbles: true }));
    }
    if (inputs?.[1]) {
      inputs[1].value = "synthetic-password";
      inputs[1].dispatchEvent(new Event("input", { bubbles: true }));
    }
  });
  await act(async () => container?.querySelector<HTMLFormElement>("form")?.dispatchEvent(
    new Event("submit", { bubbles: true, cancelable: true }),
  ));
  await vi.waitFor(() => expect(container?.textContent).toContain(replacementActor.display_name));
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
  configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: null });
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("Phase 15C canonical route ownership", () => {
  it("P15C-NAV-01 gives every screen a direct stable route and active parent navigation", async () => {
    const entries = [
      [paths.dashboard, "dashboard", paths.dashboard],
      [paths.newOnboarding, "new-onboarding", paths.newOnboarding],
      [paths.retainedIntake(CASE_A), `intake:${CASE_A}`, paths.newOnboarding],
      [paths.cases, "cases", paths.cases],
      [paths.caseDetail(CASE_A), `case:${CASE_A}`, paths.cases],
      [paths.onboarded, "onboarded", paths.onboarded],
      [paths.onboardedDetail(CASE_A), `client:${CASE_A}`, paths.onboarded],
      [paths.audit, "audit", paths.audit],
      [paths.auditCase(CASE_A), `audit:${CASE_A}`, paths.audit],
      [paths.policy, "policy", paths.policy],
      [paths.adminUsers, "users", paths.adminUsers],
      [paths.adminTeams, "teams", paths.adminTeams],
    ] as const;

    for (const [path, screen, activeHref] of entries) {
      await act(async () => root?.render(
        <MemoryRouter key={path} initialEntries={[path]}><RouteFixture /></MemoryRouter>,
      ));
      expect(container?.querySelector("[data-testid='screen']")?.textContent).toBe(screen);
      expect(container?.querySelector("[data-testid='location']")?.textContent).toBe(path);
      expect(container?.querySelector<HTMLAnchorElement>("a[aria-current='page']")?.getAttribute("href"))
        .toBe(activeHref);
    }
  });

  it("P15C-NAV-02 replaces root with a capability-safe default", async () => {
    expect(defaultPathForProfile(actor)).toBe(paths.dashboard);
    expect(defaultPathForProfile(hrActor)).toBe(paths.adminUsers);

    await act(async () => root?.render(
      <MemoryRouter initialEntries={[paths.root]}><RouteFixture profile={hrActor} /></MemoryRouter>,
    ));
    await vi.waitFor(() => expect(container?.querySelector("[data-testid='location']")?.textContent)
      .toBe(paths.adminUsers));
    expect(container?.textContent).toContain("users");
    expect(container?.textContent).not.toContain("dashboard");

    await act(async () => root?.render(
      <MemoryRouter key={paths.goldtierSandbox} initialEntries={[paths.goldtierSandbox]}><RouteFixture profile={hrActor} /></MemoryRouter>,
    ));
    expect(container?.querySelector("[data-testid='screen']")?.textContent).toBe("goldtier-sandbox");
    expect(requiredCapabilityForPath(paths.goldtierSandbox)).toBe("PROVIDER_SANDBOX_TEST");
  });

  it("P15C-NAV-03 restores exact case URLs through Back and Forward", async () => {
    function HistoryHarness() {
      const navigate = useNavigate();
      return (
        <>
          <button type="button" onClick={() => navigate(paths.caseDetail(CASE_B))}>Open B</button>
          <button type="button" onClick={() => navigate(-1)}>Back</button>
          <button type="button" onClick={() => navigate(1)}>Forward</button>
          <Routes><Route path={routePatterns.caseDetail} element={<LocationProbe />} /></Routes>
        </>
      );
    }
    await act(async () => root?.render(
      <MemoryRouter initialEntries={[paths.caseDetail(CASE_A)]}><HistoryHarness /></MemoryRouter>,
    ));
    const buttons = container?.querySelectorAll<HTMLButtonElement>("button");
    await act(async () => buttons?.[0].click());
    expect(container?.querySelector("output")?.textContent).toBe(paths.caseDetail(CASE_B));
    await act(async () => buttons?.[1].click());
    expect(container?.querySelector("output")?.textContent).toBe(paths.caseDetail(CASE_A));
    await act(async () => buttons?.[2].click());
    expect(container?.querySelector("output")?.textContent).toBe(paths.caseDetail(CASE_B));
  });

  it("P15C-NAV-04 exposes a real same-origin case href without row-wide navigation", async () => {
    const queryClient = testClient();
    queryClient.setQueryData(
      caseQueryKeys.casePortfolio(actor.user_id, {
        priority: "all",
        prioritySort: "highest_first",
        teamFilter: "all",
        offset: 0,
        limit: 50,
      }),
      { items: [listItem], offset: 0, limit: 50, has_more: false },
    );
    await act(async () => root?.render(
      <MemoryRouter initialEntries={[paths.cases]}>
        <QueryClientProvider client={queryClient}>
          <CaseQueue actor={actor} presentation={DEFAULT_CASE_QUEUE_PRESENTATION} onPresentationChange={() => undefined} />
        </QueryClientProvider>
      </MemoryRouter>,
    ));
    const open = Array.from(container?.querySelectorAll<HTMLAnchorElement>("a") ?? [])
      .find((link) => link.textContent === "Open");
    expect(open?.getAttribute("href")).toBe(paths.caseDetail(CASE_A));
    expect(open?.closest("tr")?.hasAttribute("tabindex")).toBe(false);
    expect(open?.closest("tr")?.getAttribute("role")).toBeNull();
  });

  it("shows every accessible completed case by default and applies active Onboarded filters", async () => {
    const completedA = {
      ...listItem,
      status: "COMPLETED" as const,
      current_stage: "COMPLETE" as const,
      completed_at: NOW,
      final_outcome: "MOCK_GOLDTIER_SUBMITTED",
      mock_goldtier_party_id: "GT-CUSTOMER-A",
    };
    const completedB = {
      ...completedA,
      case_id: CASE_B,
      requested_uen: "202400002B",
      legal_name: "SYNTHETIC AUSTRALIA PTY LTD",
      resolved_jurisdiction: "AU",
      mock_goldtier_party_id: "GT-CUSTOMER-B",
    };
    const queryClient = testClient();
    queryClient.setQueryData(
      caseQueryKeys.caseList(
        actor.user_id,
        "COMPLETED",
        "all",
        "highest_first",
        "all",
        undefined,
      ),
      [completedA, completedB],
    );

    await act(async () => root?.render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <OnboardedClients actor={actor} />
        </QueryClientProvider>
      </MemoryRouter>,
    ));

    expect(container?.textContent).toContain(CASE_A);
    expect(container?.textContent).toContain(CASE_B);
    const jurisdiction = Array.from(container?.querySelectorAll<HTMLSelectElement>("select") ?? [])
      .find((select) => select.options[0]?.textContent === "Jurisdiction: All")!;
    await act(async () => {
      jurisdiction.value = "AU";
      jurisdiction.dispatchEvent(new Event("change", { bubbles: true }));
    });
    expect(container?.textContent).not.toContain(CASE_A);
    expect(container?.textContent).toContain(CASE_B);

    const search = container?.querySelector<HTMLInputElement>(
      'input[placeholder="Search client, UEN / ACN, or company…"]',
    )!;
    await act(async () => {
      jurisdiction.value = "";
      jurisdiction.dispatchEvent(new Event("change", { bubbles: true }));
    });
    await act(async () => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(
        search,
        "202400001A",
      );
      search.dispatchEvent(new Event("input", { bubbles: true }));
    });
    expect(container?.textContent).toContain(CASE_A);
    expect(container?.textContent).not.toContain(CASE_B);
  });

  it("P15C-NAV-05 keeps unknown, malformed, and capability-unavailable routes generic and inert", async () => {
    const request = vi.spyOn(globalThis, "fetch");
    for (const path of ["/unknown/private-value", "/cases/not-a-case-id", paths.adminUsers, paths.goldtierSandbox]) {
      await act(async () => root?.render(
        <MemoryRouter key={path} initialEntries={[path]}>
          <QueryClientProvider client={testClient()}><App actor={actor} onLogout={() => undefined} /></QueryClientProvider>
        </MemoryRouter>,
      ));
      expect(container?.textContent).toContain("Page unavailable");
      expect(container?.textContent).not.toContain("not-a-case-id");
    }
    expect(request).not.toHaveBeenCalled();
    expect(requiredCapabilityForPath("/api/does-not-exist")).toBeNull();
    expect(requiredCapabilityForPath("/assets/does-not-exist.js")).toBeNull();
  });
});

describe("Phase 15C case-bound action lifetime", () => {
  it("renders each reconciliation action once through the shared intervention panel", async () => {
    const summary = caseDetailFixture(CASE_A, "CASE A");
    const exception = {
      ...summary.active_exceptions[0],
      blocker_code: "DOCUMENT_SOURCE_CONFLICT",
      available_actions: ["KEEP_REGISTRY_VALUE"],
      evidence_version: "reconciliation:1:1:synthetic",
    } as ZeroTouchException;
    const observation = {
      observation_id: "observation-registry",
      field_name: "legal_name",
      normalized_value: "CASE A",
      source_kind: "REGISTRY",
      source_system: "ACRA",
      environment: "MOCK",
      observed_at: NOW,
      evidence_reference: "safe:registry",
      document_id: null,
      document_display_name: null,
      confidence: null,
      validity: "VALID",
    } as const;
    const reviewSummary = {
      ...summary,
      active_exceptions: [exception],
      interventions: [{
        intervention_id: exception.exception_id,
        owning_stage: "DOCUMENT",
        owning_stage_label: "Documents / reconciliation",
        title: "Document or reconciliation review required",
        blocker_code: exception.blocker_code,
        explanation: exception.explanation,
        required_evidence_or_input: ["Current document evidence."],
        authorized_actions: [{
          action: "KEEP_REGISTRY_VALUE",
          label: "Keep registry value",
          description: "Retain the current registry observation.",
        }],
        no_action_reason: null,
        expected_next_step: "The owning service will re-evaluate retained evidence.",
        candidate_summaries: [],
      }],
      reconciliation: {
        reconciliation_id: "reconciliation-1",
        version: 1,
        status: "REVIEW_REQUIRED",
        source_document_ids: [documentFixture(CASE_A).document_id],
        source_document_event_counts: [0],
        fields: [{
          field_name: "legal_name",
          observations: [observation],
          outcome: "CONFLICT",
          document_required: true,
          discrepancy_id: exception.exception_id,
        }],
        discrepancies: [{
          discrepancy_id: exception.exception_id,
          field_name: "legal_name",
          outcome: "CONFLICT",
          observations: [observation],
          status: "OPEN",
          allowed_actions: ["KEEP_REGISTRY_VALUE"],
          evidence_fingerprint: "a".repeat(64),
          decision: null,
        }],
        updated_at: NOW,
      },
    } as unknown as ZeroTouchCaseSummary;
    const queryClient = testClient();
    queryClient.setQueryData(
      caseQueryKeys.detail(relationshipActor.user_id, CASE_A),
      reviewSummary,
    );
    queryClient.setQueryData(
      caseQueryKeys.documents(relationshipActor.user_id, CASE_A),
      [documentFixture(CASE_A)],
    );
    queryClient.setQueryData(caseQueryKeys.ownership(relationshipActor.user_id, CASE_A), null);
    queryClient.setQueryData(caseQueryKeys.intelligence(relationshipActor.user_id, CASE_A), null);

    await act(async () => root?.render(
      <QueryClientProvider client={queryClient}>
        <CaseDetail
          caseId={CASE_A}
          actor={relationshipActor}
          onBack={() => undefined}
          onViewOnboarded={() => undefined}
          onViewAudit={() => undefined}
        />
      </QueryClientProvider>,
    ));

    const actions = Array.from(container?.querySelectorAll<HTMLButtonElement>("button") ?? [])
      .filter((button) => button.textContent === "Keep registry value");
    expect(actions).toHaveLength(1);
    expect(container?.textContent).toContain(
      "Use the backend-authorized Action required panel to record this decision.",
    );
  });

  it("closes A delete and correction state when the routed identity changes to B and omits unsupported actions", async () => {
    const request = vi.spyOn(globalThis, "fetch");
    const queryClient = testClient();
    seedCaseDetail(queryClient, CASE_A, "CASE A");
    seedCaseDetail(queryClient, CASE_B, "CASE B");
    await act(async () => root?.render(
      <MemoryRouter initialEntries={[paths.caseDetail(CASE_A)]}>
        <QueryClientProvider client={queryClient}>
          <CaseDetailRouteHarness onBack={() => undefined} />
        </QueryClientProvider>
      </MemoryRouter>,
    ));

    const click = async (label: string) => {
      const target = Array.from(container?.querySelectorAll<HTMLElement>("button, a") ?? [])
        .find((item) => item.textContent === label);
      await act(async () => target?.click());
    };

    await click("Delete case");
    expect(container?.textContent).toContain("Delete case permanently?");
    await click("Open B");
    await vi.waitFor(() => expect(container?.querySelector("h1")?.textContent).toBe("CASE B"));
    expect(container?.textContent).not.toContain("Delete case permanently?");

    await click("Open A");
    await act(async () => {
      container!.querySelector<HTMLInputElement>('input[data-review-field="legal_name"][value="CORRECTED"]')!.click();
    });
    expect(container?.querySelector<HTMLInputElement>('#case-blocker-review input[data-review-field="legal_name"]:checked')?.value).toBe("CORRECTED");
    await click("Open B");
    expect(container?.querySelector<HTMLInputElement>('#case-blocker-review input[data-review-field="legal_name"]:checked')?.value ?? "REJECTED").toBe("REJECTED");
    expect(container?.textContent).not.toMatch(/Assign reviewer|Return for rework/);
    expect(request.mock.calls.filter(([, init]) => init?.method === "DELETE")).toHaveLength(0);
  });

  it("contains a pending A delete success after navigation to B", async () => {
    const pendingDelete = deferred<Response>();
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if (init?.method === "DELETE" && String(input).endsWith(CASE_A)) return pendingDelete.promise;
      return unavailable();
    });
    const queryClient = testClient();
    seedCaseDetail(queryClient, CASE_A, "CASE A");
    seedCaseDetail(queryClient, CASE_B, "CASE B");
    const onBack = vi.fn();
    await act(async () => root?.render(
      <MemoryRouter initialEntries={[paths.caseDetail(CASE_A)]}>
        <QueryClientProvider client={queryClient}>
          <CaseDetailRouteHarness onBack={onBack} />
        </QueryClientProvider>
      </MemoryRouter>,
    ));
    const deleteButton = Array.from(container?.querySelectorAll<HTMLButtonElement>("button") ?? [])
      .find((button) => button.textContent === "Delete case");
    await act(async () => deleteButton?.click());
    await act(async () => container?.querySelector<HTMLButtonElement>(".delete-case-dialog .btn-danger")?.click());
    await vi.waitFor(() => expect(request.mock.calls.filter(([, init]) => init?.method === "DELETE")).toHaveLength(1));
    const openB = Array.from(container?.querySelectorAll<HTMLAnchorElement>("a") ?? [])
      .find((link) => link.textContent === "Open B");
    await act(async () => openB?.click());
    await vi.waitFor(() => expect(container?.querySelector("h1")?.textContent).toBe("CASE B"));

    await act(async () => {
      pendingDelete.resolve(new Response(null, { status: 204 }));
      await pendingDelete.promise;
      await Promise.resolve();
    });
    await vi.waitFor(() => expect(container?.querySelector("[data-testid='location']")?.textContent)
      .toBe(paths.caseDetail(CASE_B)));
    expect(container?.querySelector("h1")?.textContent).toBe("CASE B");
    expect(onBack).not.toHaveBeenCalled();
    expect(request.mock.calls.filter(([url, init]) => init?.method === "DELETE" && String(url).endsWith(CASE_B))).toHaveLength(0);
  });

  it("contains a pending A delete failure after navigation to B", async () => {
    const pendingDelete = deferred<Response>();
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if (init?.method === "DELETE" && String(input).endsWith(CASE_A)) return pendingDelete.promise;
      return unavailable();
    });
    const queryClient = testClient();
    seedCaseDetail(queryClient, CASE_A, "CASE A");
    seedCaseDetail(queryClient, CASE_B, "CASE B");
    const onBack = vi.fn();
    await act(async () => root?.render(
      <MemoryRouter initialEntries={[paths.caseDetail(CASE_A)]}>
        <QueryClientProvider client={queryClient}>
          <CaseDetailRouteHarness onBack={onBack} />
        </QueryClientProvider>
      </MemoryRouter>,
    ));
    const deleteButton = Array.from(container?.querySelectorAll<HTMLButtonElement>("button") ?? [])
      .find((button) => button.textContent === "Delete case");
    await act(async () => deleteButton?.click());
    await act(async () => container?.querySelector<HTMLButtonElement>(".delete-case-dialog .btn-danger")?.click());
    await vi.waitFor(() => expect(request.mock.calls.filter(([, init]) => init?.method === "DELETE")).toHaveLength(1));
    const openB = Array.from(container?.querySelectorAll<HTMLAnchorElement>("a") ?? [])
      .find((link) => link.textContent === "Open B");
    await act(async () => openB?.click());
    await vi.waitFor(() => expect(container?.querySelector("h1")?.textContent).toBe("CASE B"));

    await act(async () => {
      pendingDelete.reject(new Error("Synthetic A deletion failure"));
      await pendingDelete.promise.catch(() => undefined);
      await Promise.resolve();
    });
    expect(container?.querySelector("[data-testid='location']")?.textContent).toBe(paths.caseDetail(CASE_B));
    expect(container?.textContent).toContain("CASE B");
    expect(container?.textContent).not.toContain("Synthetic A deletion failure");
    expect(onBack).not.toHaveBeenCalled();
  });

  it.each(["success", "failure"] as const)(
    "contains a pending A review %s after navigation to B and rejects same-tick duplicates",
    async (outcome) => {
      const pendingReview = deferred<Response>();
      const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
        if (init?.method === "POST" && String(input).endsWith("/review-decisions")) return pendingReview.promise;
        return unavailable();
      });
      const queryClient = testClient();
      seedCaseDetail(queryClient, CASE_A, "CASE A");
      seedCaseDetail(queryClient, CASE_B, "CASE B");
      await act(async () => root?.render(
        <MemoryRouter initialEntries={[paths.caseDetail(CASE_A)]}>
          <QueryClientProvider client={queryClient}>
            <CaseDetailRouteHarness onBack={() => undefined} />
          </QueryClientProvider>
        </MemoryRouter>,
      ));

      const accept = await acceptDraftControl();
      act(() => {
        accept.click();
        accept.click();
      });
      await vi.waitFor(() => expect(request.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1));
      const openB = Array.from(container?.querySelectorAll<HTMLAnchorElement>("a") ?? [])
        .find((link) => link.textContent === "Open B")!;
      await act(async () => openB.click());
      await vi.waitFor(() => expect(container?.querySelector("h1")?.textContent).toBe("CASE B"));

      await act(async () => {
        if (outcome === "success") pendingReview.resolve(json(documentFixture(CASE_A)));
        else pendingReview.reject(new TypeError("Synthetic uncertain A review"));
        await pendingReview.promise.catch(() => undefined);
        await Promise.resolve();
      });

      expect(container?.querySelector("h1")?.textContent).toBe("CASE B");
      expect(container?.textContent).not.toContain("Synthetic uncertain A review");
      expect(request.mock.calls.filter(([url, init]) => init?.method === "POST" && String(url).includes(CASE_B))).toHaveLength(0);
    },
  );

  it("prevents an older documents query from overwriting an authoritative review refresh", async () => {
    const staleDocuments = deferred<Response>();
    const reviewedDocument = {
      ...documentFixture(CASE_A),
      fields: documentFixture(CASE_A).fields.map((field) => ({
        ...field,
        review_status: "ACCEPTED" as const,
        reviewed_value: field.normalized_value,
        reviewed_at: NOW,
      })),
    };
    let documentReads = 0;
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (init?.method === "POST" && url.endsWith("/review-decisions")) return json(reviewedDocument);
      if (url.endsWith(`/api/clm/zero-touch/cases/${CASE_A}`)) {
        return json(caseDetailFixture(CASE_A, "CASE A"));
      }
      if (url.endsWith(`/api/onboarding/cases/${CASE_A}/documents`)) {
        documentReads += 1;
        return documentReads === 1 ? staleDocuments.promise : json([reviewedDocument]);
      }
      if (url.endsWith(`/api/onboarding/cases/${CASE_A}/ownership`)) return unavailable();
      return unavailable();
    });
    const queryClient = testClient();
    seedCaseDetail(queryClient, CASE_A, "CASE A");
    await act(async () => root?.render(
      <QueryClientProvider client={queryClient}>
        <CaseDetail caseId={CASE_A} actor={relationshipActor} onBack={() => undefined} onViewOnboarded={() => undefined} onViewAudit={() => undefined} />
      </QueryClientProvider>,
    ));

    void queryClient.invalidateQueries({
      queryKey: caseQueryKeys.documents(relationshipActor.user_id, CASE_A),
      exact: true,
    });
    await vi.waitFor(() => expect(documentReads).toBe(1));
    const accept = await acceptDraftControl();
    await act(async () => {
      accept.click();
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    await vi.waitFor(() => expect(container?.textContent).toContain("1 final / 1 fields"));

    await act(async () => {
      staleDocuments.resolve(json([documentFixture(CASE_A)]));
      await staleDocuments.promise;
      await Promise.resolve();
    });
    expect(container?.textContent).toContain("1 final / 1 fields");
    expect(container?.textContent).not.toContain("0 final / 1 fields");
  });

  it("publishes reviewed documents without waiting for unrelated ownership refresh completion", async () => {
    const pendingOwnership = deferred<Response>();
    const reviewedDocument = {
      ...documentFixture(CASE_A),
      fields: documentFixture(CASE_A).fields.map((field) => ({
        ...field,
        review_status: "ACCEPTED" as const,
        reviewed_value: field.normalized_value,
        reviewed_at: NOW,
      })),
    };
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (init?.method === "POST" && url.endsWith("/review-decisions")) return json(reviewedDocument);
      if (url.endsWith(`/api/clm/zero-touch/cases/${CASE_A}`)) {
        return json(caseDetailFixture(CASE_A, "CASE A"));
      }
      if (url.endsWith(`/api/onboarding/cases/${CASE_A}/documents`)) {
        return json([reviewedDocument]);
      }
      if (url.endsWith(`/api/onboarding/cases/${CASE_A}/ownership`)) {
        return pendingOwnership.promise;
      }
      return unavailable();
    });
    const queryClient = testClient();
    seedCaseDetail(queryClient, CASE_A, "CASE A");
    await act(async () => root?.render(
      <QueryClientProvider client={queryClient}>
        <CaseDetail caseId={CASE_A} actor={relationshipActor} onBack={() => undefined} onViewOnboarded={() => undefined} onViewAudit={() => undefined} />
      </QueryClientProvider>,
    ));

    const accept = await acceptDraftControl();
    await act(async () => {
      accept.click();
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    await vi.waitFor(() => expect(container?.textContent).toContain("1 final / 1 fields"));
    expect(container?.textContent).not.toContain("0 final / 1 fields");

    await act(async () => {
      pendingOwnership.resolve(unavailable());
      await pendingOwnership.promise;
    });
  });

  it("contains a pending review after actor replacement on the same case", async () => {
    const pendingReview = deferred<Response>();
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if (init?.method === "POST" && String(input).endsWith("/review-decisions")) return pendingReview.promise;
      return unavailable();
    });
    const queryClient = testClient();
    seedCaseDetail(queryClient, CASE_A, "CASE A");
    queryClient.setQueryData(caseQueryKeys.detail(replacementActor.user_id, CASE_A), {
      ...caseDetailFixture(CASE_A, "CASE A REPLACEMENT ACTOR"),
      evidence_decision_authorized: false,
    });
    queryClient.setQueryData(caseQueryKeys.documents(replacementActor.user_id, CASE_A), [documentFixture(CASE_A)]);
    queryClient.setQueryData(caseQueryKeys.ownership(replacementActor.user_id, CASE_A), null);

    await act(async () => root?.render(
      <QueryClientProvider client={queryClient}>
        <CaseDetail caseId={CASE_A} actor={relationshipActor} onBack={() => undefined} onViewOnboarded={() => undefined} onViewAudit={() => undefined} />
      </QueryClientProvider>,
    ));
    const accept = await acceptDraftControl();
    await act(async () => accept.click());
    await vi.waitFor(() => expect(request.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1));

    await act(async () => root?.render(
      <QueryClientProvider client={queryClient}>
        <CaseDetail caseId={CASE_A} actor={replacementActor} onBack={() => undefined} onViewOnboarded={() => undefined} onViewAudit={() => undefined} />
      </QueryClientProvider>,
    ));
    await vi.waitFor(() => expect(container?.querySelector("h1")?.textContent).toBe("CASE A REPLACEMENT ACTOR"));
    await act(async () => {
      pendingReview.reject(new TypeError("Old actor uncertain review"));
      await pendingReview.promise.catch(() => undefined);
      await Promise.resolve();
    });

    expect(container?.textContent).toContain("CASE A REPLACEMENT ACTOR");
    expect(container?.textContent).toContain("Evidence decisions are read-only for this viewer.");
    const replacementAccept = await acceptDraftControl();
    expect(replacementAccept.disabled).toBe(true);
    act(() => replacementAccept.click());
    expect(container?.textContent).not.toContain("Old actor uncertain review");
    expect(request.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
  });

  it("serializes priority and delete controls behind a pending evidence mutation", async () => {
    const pendingReview = deferred<Response>();
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if (init?.method === "POST" && String(input).endsWith("/review-decisions")) return pendingReview.promise;
      return unavailable();
    });
    const queryClient = testClient();
    seedCaseDetail(queryClient, CASE_A, "CASE A");
    await act(async () => root?.render(
      <MemoryRouter initialEntries={[paths.caseDetail(CASE_A)]}>
        <QueryClientProvider client={queryClient}>
          <CaseDetailRouteHarness onBack={() => undefined} />
        </QueryClientProvider>
      </MemoryRouter>,
    ));

    const accept = await acceptDraftControl();
    await act(async () => accept.click());
    await vi.waitFor(() => expect(request.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1));
    expect(container?.querySelector<HTMLSelectElement>(".priority-select")?.disabled).toBe(true);
    expect(Array.from(container?.querySelectorAll<HTMLButtonElement>("button") ?? []).find((button) => button.textContent === "Set")?.disabled).toBe(true);
    expect(Array.from(container?.querySelectorAll<HTMLButtonElement>("button") ?? []).find((button) => button.textContent === "Delete case")?.disabled).toBe(true);

    await act(async () => {
      pendingReview.resolve(json(documentFixture(CASE_A)));
      await pendingReview.promise;
    });
  });

  it("serializes evidence and delete controls behind a pending priority mutation", async () => {
    const pendingPriority = deferred<Response>();
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, init) => {
      if (init?.method === "PATCH") return pendingPriority.promise;
      return unavailable();
    });
    const queryClient = testClient();
    seedCaseDetail(queryClient, CASE_A, "CASE A");
    await act(async () => root?.render(
      <MemoryRouter initialEntries={[paths.caseDetail(CASE_A)]}>
        <QueryClientProvider client={queryClient}>
          <CaseDetailRouteHarness onBack={() => undefined} />
        </QueryClientProvider>
      </MemoryRouter>,
    ));

    const setPriority = Array.from(container?.querySelectorAll<HTMLButtonElement>("button") ?? [])
      .find((button) => button.textContent === "Set")!;
    await act(async () => setPriority.click());
    await vi.waitFor(() => expect(request.mock.calls.filter(([, init]) => init?.method === "PATCH")).toHaveLength(1));
    const accept = await acceptDraftControl();
    const deleteButton = Array.from(container?.querySelectorAll<HTMLButtonElement>("button") ?? [])
      .find((button) => button.textContent === "Delete case")!;
    expect(accept.disabled).toBe(true);
    expect(deleteButton.disabled).toBe(true);
    act(() => accept.click());
    expect(request.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0);

    await act(async () => {
      pendingPriority.resolve(json({ case_id: CASE_A, priority: null }));
      await pendingPriority.promise;
    });
  });

  it.each([true, false])("requires an explicit intended count for initial intake; authorized=%s", async (authorized) => {
    const initial = { ...caseDetailFixture(CASE_A, "CASE A"), status: "PENDING_INPUTS" as const,
      evidence_decision_authorized: authorized,
      timing: { ...caseDetailFixture(CASE_A, "CASE A").timing, automation_elapsed_ms: null } };
    const completed = { ...initial, version: initial.version + 1, status: "WAITING_FOR_REVIEW" as const,
      current_stage: "READINESS" as const, timing: { ...initial.timing, automation_elapsed_ms: 0 } };
    let published: ZeroTouchCaseSummary = initial;
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (init?.method === "POST" && url.endsWith("/intake/complete")) {
        expect(JSON.parse(String(init.body))).toEqual({ expected_document_count: 2 });
        published = completed;
        return json(completed);
      }
      if (url.endsWith(`/api/clm/zero-touch/cases/${CASE_A}`)) return json(published);
      if (url.endsWith("/documents")) return json([documentFixture(CASE_A)]);
      return unavailable();
    });
    const queryClient = testClient();
    queryClient.setQueryData(caseQueryKeys.detail(relationshipActor.user_id, CASE_A), initial);
    queryClient.setQueryData(caseQueryKeys.documents(relationshipActor.user_id, CASE_A), [documentFixture(CASE_A)]);
    queryClient.setQueryData(caseQueryKeys.ownership(relationshipActor.user_id, CASE_A), null);
    queryClient.setQueryData(caseQueryKeys.intelligence(relationshipActor.user_id, CASE_A), null);
    await act(async () => root?.render(<QueryClientProvider client={queryClient}>
      <CaseDetail caseId={CASE_A} actor={relationshipActor} onBack={() => undefined} onViewOnboarded={() => undefined} onViewAudit={() => undefined} />
    </QueryClientProvider>));
    const count = container?.querySelector<HTMLInputElement>('input[name="expectedDocumentCount"]');
    expect(count).toBeTruthy();
    expect(count!.value).toBe("");
    expect(count!.disabled).toBe(!authorized);
    const form = count!.closest("form")!;
    const submit = form.querySelector<HTMLButtonElement>('button[type="submit"]')!;
    expect(submit.textContent).toBe("Complete document intake");
    expect(submit.disabled).toBe(!authorized);
    expect(request.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0);
    if (authorized) {
      await act(async () => { count!.value = "2"; form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })); });
      await vi.waitFor(() => expect(request.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1));
      expect(request.mock.calls.some(([input]) => String(input).endsWith("/resume"))).toBe(false);
      await vi.waitFor(() => expect(container?.querySelector('input[name="expectedDocumentCount"]')).toBeNull());
    }
  });

  it.each(["accepted", "continuation-failed"] as const)(
    "submits one targeted retry and authoritatively refreshes all case evidence after %s",
    async (outcome) => {
    const failed = {
      ...documentFixture(CASE_A),
      state: "FAILED" as const,
      error: { code: "DOCUMENT_REUPLOAD_REQUIRED", message: "Retry required" },
    };
    const recovered = {
      ...documentFixture(CASE_A),
      document_id: "00000000-0000-4000-8000-000000000151",
      supersedes_document_id: failed.document_id,
    };
    const historical = { ...failed, superseded_by_document_id: recovered.document_id };
    const refreshedSummary = outcome === "accepted"
      ? { ...caseDetailFixture(CASE_A, "CASE A"), status: "PENDING_INPUTS" as const }
      : { ...caseDetailFixture(CASE_A, "CASE A"), status: "TECHNICAL_FAILURE" as const,
          current_stage: "OWNERSHIP" as const,
          technical_failure: { code: "OWNERSHIP_PERSISTENCE_UNAVAILABLE",
            message: "Ownership evidence is unavailable." } };
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (init?.method === "POST" && url.endsWith(`/intake/documents/${failed.document_id}/retry`)) {
        return outcome === "accepted" ? json(recovered) : json({ detail: {
          code: "OWNERSHIP_PERSISTENCE_UNAVAILABLE", message: "Ownership evidence is unavailable.",
          case_id: CASE_A, automation_id: refreshedSummary.automation_id,
        } }, 503);
      }
      if (url.endsWith(`/api/clm/zero-touch/cases/${CASE_A}`)) return json(refreshedSummary);
      if (url.endsWith(`/api/onboarding/cases/${CASE_A}/documents`)) return json([historical, recovered]);
      if (url.endsWith(`/api/onboarding/cases/${CASE_A}/ownership`)) return unavailable();
      return unavailable();
    });
    const queryClient = testClient();
    queryClient.setQueryData(caseQueryKeys.detail(relationshipActor.user_id, CASE_A), {
      ...caseDetailFixture(CASE_A, "CASE A"), status: "PENDING_INPUTS" as const,
    });
    queryClient.setQueryData(caseQueryKeys.documents(relationshipActor.user_id, CASE_A), [failed]);
    queryClient.setQueryData(caseQueryKeys.ownership(relationshipActor.user_id, CASE_A), null);
    queryClient.setQueryData(caseQueryKeys.intelligence(relationshipActor.user_id, CASE_A), null);
    await act(async () => root?.render(
      <QueryClientProvider client={queryClient}>
        <CaseDetail caseId={CASE_A} actor={relationshipActor} onBack={() => undefined} onViewOnboarded={() => undefined} onViewAudit={() => undefined} />
      </QueryClientProvider>,
    ));

    const input = container?.querySelector<HTMLInputElement>(".document-card .document-upload-input")!;
    const file = new File(["safe synthetic retry"], "retry.txt", { type: "text/plain" });
    Object.defineProperty(input, "files", { configurable: true, value: [file] });
    await act(async () => input.dispatchEvent(new Event("change", { bubbles: true })));
    await vi.waitFor(() => expect(container?.textContent).toContain("Evidence history (1)"));

    const posts = request.mock.calls.filter(([, init]) => init?.method === "POST");
    expect(posts).toHaveLength(1);
    expect(String(posts[0][0])).toContain(`/intake/documents/${failed.document_id}/retry`);
    expect(request.mock.calls.filter(([, init]) => !init?.method || init.method === "GET")).toHaveLength(4);
    if (outcome === "continuation-failed") {
      expect(container?.textContent).toContain("The outcome could not be confirmed. Current case evidence was reloaded");
      expect(queryClient.getQueryData(caseQueryKeys.detail(relationshipActor.user_id, CASE_A)))
        .toEqual(refreshedSummary);
      expect(container?.querySelector(".document-card .document-upload-input")).toBeNull();
      expect(request.mock.calls.filter(([url]) => String(url).endsWith("/resume"))).toHaveLength(0);
    }
  });

  it("locks mutations after review success plus refresh failure and exposes only read-only refresh recovery", async () => {
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      if (init?.method === "POST" && String(input).endsWith("/review-decisions")) return json(documentFixture(CASE_A));
      return json({ detail: { code: "UNAVAILABLE", message: "Temporarily unavailable" } }, 503);
    });
    const queryClient = testClient();
    seedCaseDetail(queryClient, CASE_A, "CASE A");
    await act(async () => root?.render(
      <MemoryRouter initialEntries={[paths.caseDetail(CASE_A)]}>
        <QueryClientProvider client={queryClient}>
          <CaseDetailRouteHarness onBack={() => undefined} />
        </QueryClientProvider>
      </MemoryRouter>,
    ));
    const accept = await acceptDraftControl();
    await act(async () => accept.click());
    await vi.waitFor(() => expect(container?.textContent).toContain("Evidence reload could not be confirmed."));
    expect(request.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
    const reject = container!.querySelector<HTMLInputElement>('input[data-review-field="legal_name"][value="REJECTED"]')!;
    expect(reject.disabled).toBe(true);
    const refresh = Array.from(container?.querySelectorAll<HTMLButtonElement>("button") ?? [])
      .find((button) => button.textContent === "Refresh case evidence")!;
    expect(refresh.disabled).toBe(false);
    await act(async () => refresh.click());
    await vi.waitFor(() => expect(container?.textContent).toContain("Case evidence could not be refreshed."));
    expect(request.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
  });

  it.each(["409", "503", "network"] as const)(
    "refreshes authoritative evidence once after a %s review outcome without replay or resume",
    async (outcome) => {
      const refreshedSummary = caseDetailFixture(CASE_A, "CASE A REFRESHED");
      const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
        const url = String(input);
        if (init?.method === "POST" && url.endsWith("/review-decisions")) {
          if (outcome === "network") throw new TypeError("uncertain transport");
          return json({ detail: { code: `REVIEW_${outcome}`, message: "Safe review outcome" } }, Number(outcome));
        }
        if (url.endsWith(`/api/clm/zero-touch/cases/${CASE_A}`)) return json(refreshedSummary);
        if (url.endsWith(`/api/onboarding/cases/${CASE_A}/documents`)) return json([documentFixture(CASE_A)]);
        if (url.endsWith(`/api/onboarding/cases/${CASE_A}/ownership`)) return unavailable();
        return unavailable();
      });
      const queryClient = testClient();
      seedCaseDetail(queryClient, CASE_A, "CASE A");
      await act(async () => root?.render(
        <MemoryRouter initialEntries={[paths.caseDetail(CASE_A)]}>
          <QueryClientProvider client={queryClient}>
            <CaseDetailRouteHarness onBack={() => undefined} />
          </QueryClientProvider>
        </MemoryRouter>,
      ));
      const accept = await acceptDraftControl();
      await act(async () => accept.click());
      await vi.waitFor(() => expect(container?.querySelector("h1")?.textContent).toBe("CASE A REFRESHED"));

      const posts = request.mock.calls.filter(([, init]) => init?.method === "POST");
      expect(posts).toHaveLength(1);
      expect(String(posts[0][0])).toBe(`/api/clm/zero-touch/cases/${CASE_A}/review-decisions`);
      expect(JSON.parse(String(posts[0][1]?.body))).toEqual({
        expected_automation_version: 1, expected_case_event_count: 1,
        documents: [{ document_id: documentFixture(CASE_A).document_id, expected_event_count: 0,
          source_fingerprint: "a".repeat(64), decisions: [{ field_key: "legal_name", decision: "ACCEPTED" }] }],
      });
      expect(request.mock.calls.filter(([url]) => String(url).endsWith("/resume"))).toHaveLength(0);
      expect(request.mock.calls.filter(([, init]) => !init?.method || init.method === "GET")).toHaveLength(4);
      expect(container?.textContent).toContain(
        outcome === "409"
          ? "The evidence changed before this action. Current case evidence was reloaded."
          : "The outcome could not be confirmed. Current case evidence was reloaded",
      );
    },
  );

  it("uses the generic unavailable presentation after a review returns safe 404", async () => {
    const request = vi.spyOn(globalThis, "fetch").mockResolvedValue(unavailable());
    const queryClient = testClient();
    seedCaseDetail(queryClient, CASE_A, "CASE A");
    await act(async () => root?.render(
      <MemoryRouter initialEntries={[paths.caseDetail(CASE_A)]}>
        <QueryClientProvider client={queryClient}>
          <CaseDetailRouteHarness onBack={() => undefined} />
        </QueryClientProvider>
      </MemoryRouter>,
    ));
    const accept = await acceptDraftControl();
    await act(async () => accept.click());
    await vi.waitFor(() => expect(container?.textContent).toContain("The case is unavailable."));
    expect(container?.textContent).not.toContain("CASE A");
    expect(request.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
  });

  it("does not migrate inline correction state through browser Back and Forward", async () => {
    const queryClient = testClient();
    seedCaseDetail(queryClient, CASE_A, "CASE A");
    seedCaseDetail(queryClient, CASE_B, "CASE B");
    await act(async () => root?.render(
      <MemoryRouter initialEntries={[paths.caseDetail(CASE_A)]}>
        <QueryClientProvider client={queryClient}>
          <CaseDetailRouteHarness onBack={() => undefined} />
        </QueryClientProvider>
      </MemoryRouter>,
    ));
    const click = async (label: string) => {
      const target = Array.from(container?.querySelectorAll<HTMLElement>("button, a") ?? [])
        .find((item) => item.textContent === label);
      await act(async () => target?.click());
    };
    await act(async () => {
      container!.querySelector<HTMLInputElement>('input[data-review-field="legal_name"][value="CORRECTED"]')!.click();
    });
    expect(container?.querySelector<HTMLInputElement>('#case-blocker-review input[data-review-field="legal_name"]:checked')?.value).toBe("CORRECTED");
    await click("Open B");
    expect(container?.querySelector<HTMLInputElement>('#case-blocker-review input[data-review-field="legal_name"]:checked')?.value ?? "REJECTED").toBe("REJECTED");
    await click("History back");
    await vi.waitFor(() => expect(container?.querySelector("[data-testid='location']")?.textContent)
      .toBe(paths.caseDetail(CASE_A)));
    expect(container?.querySelector<HTMLInputElement>('#case-blocker-review input[data-review-field="legal_name"]:checked')?.value ?? 'REJECTED').toBe('REJECTED');
    await click("History forward");
    await vi.waitFor(() => expect(container?.querySelector("[data-testid='location']")?.textContent)
      .toBe(paths.caseDetail(CASE_B)));
    expect(container?.querySelector<HTMLInputElement>('#case-blocker-review input[data-review-field="legal_name"]:checked')?.value ?? 'REJECTED').toBe('REJECTED');
  });
});

describe("Phase 15C auth, cache, and adverse navigation", () => {
  it("P15C-NAV-06 presents absent, inaccessible, and deleted cases identically and removes deleted cache", async () => {
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async () => unavailable());
    const presentations: string[] = [];
    for (const caseId of [CASE_A, CASE_B, "00000000-0000-4000-8000-00000000015c"]) {
      const queryClient = testClient();
      await act(async () => root?.render(
        <MemoryRouter key={caseId}>
          <QueryClientProvider client={queryClient}>
            <RetainedIntakeRecovery actor={actor} caseId={caseId} onStartFresh={() => undefined} />
          </QueryClientProvider>
        </MemoryRouter>,
      ));
      await act(async () => { await new Promise((resolve) => setTimeout(resolve, 0)); });
      expect(container?.textContent).toContain("The case is unavailable.");
      presentations.push(container?.querySelector(".ds-banner")?.textContent ?? "");
    }
    expect(new Set(presentations)).toEqual(new Set(["The case is unavailable."]));
    expect(request.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);

    const queryClient = testClient();
    queryClient.setQueryData(caseQueryKeys.detail(actor.user_id, CASE_A), summaryFixture(CASE_A));
    await caseDeletedEffect(queryClient, actor.user_id, CASE_A);
    expect(queryClient.getQueryData(caseQueryKeys.detail(actor.user_id, CASE_A))).toBeUndefined();
  });

  it("P15C-NAV-07 preserves an anonymous deep link until interactive login resets to root", async () => {
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/api/auth/me")) return unavailable(401);
      if (url.endsWith("/api/auth/login") && init?.method === "POST") return json(session);
      if (url.includes("/api/clm/zero-touch/dashboard")) return json({});
      if (url.includes("/api/clm/zero-touch/cases")) return json([]);
      return unavailable();
    });
    function Boundary() {
      const auth = useAuth();
      const location = useLocation();
      return (
        <>
          <output data-testid="auth-location">{location.pathname}</output>
          {auth.status === "authenticated" ? <p>authenticated:{auth.session?.profile.user_id}</p> : <LoginPage />}
        </>
      );
    }
    const intended = paths.caseDetail(CASE_A);
    await act(async () => root?.render(
      <MemoryRouter initialEntries={[intended]}><AuthProvider><Boundary /></AuthProvider></MemoryRouter>,
    ));
    await vi.waitFor(() => expect(container?.textContent).toContain("Sign in"));
    expect(container?.querySelector("[data-testid='auth-location']")?.textContent).toBe(intended);
    const inputs = container?.querySelectorAll<HTMLInputElement>("input");
    await act(async () => {
      if (inputs?.[0]) { inputs[0].value = "maya-lim"; inputs[0].dispatchEvent(new Event("input", { bubbles: true })); }
      if (inputs?.[1]) { inputs[1].value = "synthetic-password"; inputs[1].dispatchEvent(new Event("input", { bubbles: true })); }
    });
    await act(async () => container?.querySelector<HTMLFormElement>("form")?.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    ));
    await vi.waitFor(() => expect(container?.textContent).toContain("authenticated:maya-lim"));
    expect(container?.querySelector("[data-testid='auth-location']")?.textContent).toBe(paths.root);
    expect(request.mock.calls.some(([url]) => String(url).includes(intended))).toBe(false);
  });

  it("P15C-NAV-08 cancels and clears user-scoped data without changing route identity", async () => {
    const queryClient = testClient();
    let aborted = false;
    const pending = queryClient.fetchQuery({
      queryKey: caseQueryKeys.detail(actor.user_id, CASE_A),
      queryFn: ({ signal }) => new Promise<never>((_resolve, reject) => {
        signal.addEventListener("abort", () => {
          aborted = true;
          reject(new DOMException("aborted", "AbortError"));
        });
      }),
    }).catch(() => undefined);
    queryClient.setQueryData(caseQueryKeys.detail("second-user", CASE_A), { private: true });
    clearSessionQueries(queryClient);
    await pending;
    expect(aborted).toBe(true);
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
    expect(paths.retainedIntake(CASE_A)).toBe(`/new-onboarding/${CASE_A}`);
  });

  it("P15C-NAV-09 aborts or confines delayed A resources and never renders them under B", async () => {
    type Release = (response: Response) => void;
    const releases: Release[] = [];
    const aSignals: AbortSignal[] = [];
    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      const url = String(input);
      if (url.includes(CASE_A)) {
        if (init?.signal) aSignals.push(init.signal);
        return new Promise<Response>((resolve) => releases.push(resolve));
      }
      if (url.includes(CASE_B) && url.includes("/documents")) return Promise.resolve(json([]));
      if (url.includes(CASE_B) && url.includes("/ownership")) return Promise.resolve(json(null));
      if (url.includes(CASE_B)) return Promise.resolve(json(summaryFixture(CASE_B, "B DATA")));
      return Promise.resolve(unavailable());
    });

    function ResourceProbe() {
      const caseId = useParams().caseId!;
      const detail = useQuery(caseDetailQueryOptions(actor.user_id, caseId));
      const documents = useQuery(documentQueryOptions(actor.user_id, caseId));
      const ownership = useQuery(ownershipQueryOptions(actor.user_id, caseId));
      return <p>{detail.data?.case.requested_uen ?? "loading"}:{documents.data?.length ?? "-"}:{ownership.data === null ? "none" : "-"}</p>;
    }
    function RaceHarness() {
      const navigate = useNavigate();
      return <><button onClick={() => navigate(paths.caseDetail(CASE_B))}>B</button><Routes><Route path={routePatterns.caseDetail} element={<ResourceProbe />} /></Routes></>;
    }
    const queryClient = testClient();
    await act(async () => root?.render(
      <MemoryRouter initialEntries={[paths.caseDetail(CASE_A)]}>
        <QueryClientProvider client={queryClient}><RaceHarness /></QueryClientProvider>
      </MemoryRouter>,
    ));
    await vi.waitFor(() => expect(releases).toHaveLength(3));
    await act(async () => {
      container?.querySelector("button")?.click();
      await Promise.all([
        queryClient.fetchQuery(caseDetailQueryOptions(actor.user_id, CASE_B)),
        queryClient.fetchQuery(documentQueryOptions(actor.user_id, CASE_B)),
        queryClient.fetchQuery(ownershipQueryOptions(actor.user_id, CASE_B)),
      ]);
    });
    expect(container?.textContent).toContain("B DATA:0:none");
    expect(aSignals).toHaveLength(3);
    expect(aSignals.every((signal) => signal.aborted)).toBe(true);
    await act(async () => {
      releases[0](json(summaryFixture(CASE_A, "A DATA")));
      releases[1](json([]));
      releases[2](json(null));
      await Promise.resolve();
    });
    expect(container?.textContent).toContain("B DATA:0:none");
    expect(container?.textContent).not.toContain("A DATA");
  });
});

describe("Phase 15C intake and mutation safety", () => {
  it("P15C-NAV-10/11 retains the case URL and selected file across route remounts without replay", async () => {
    const calls: Array<{ url: string; method: string }> = [];
    const created = summaryFixture(CASE_A);
    const completion = new Promise<Response>(() => undefined);
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      calls.push({ url, method });
      if (url.endsWith("/api/system/execution-profile")) return unavailable();
      if (url.endsWith("/api/clm/zero-touch/cases") && method === "POST") return json(created, 201);
      if (url.endsWith(`/${CASE_A}/intake/documents`) && method === "POST") return json(documentFixture(CASE_A), 201);
      if (url.endsWith(`/${CASE_A}/intake/complete`) && method === "POST") return completion;
      return unavailable();
    });
    await act(async () => root?.render(
      <MemoryRouter initialEntries={[paths.newOnboarding]}>
        <QueryClientProvider client={testClient()}>
          <StrictMode><App actor={actor} onLogout={() => undefined} /></StrictMode>
          <LocationProbe />
        </QueryClientProvider>
      </MemoryRouter>,
    ));
    const file = new File(["synthetic"], "synthetic-package.pdf", { type: "application/pdf", lastModified: 1 });
    const fileInput = Array.from(container?.querySelectorAll<HTMLInputElement>("input[type='file']") ?? [])
      .find((input) => !input.hasAttribute("webkitdirectory"));
    Object.defineProperty(fileInput, "files", { configurable: true, value: [file] });
    await act(async () => fileInput?.dispatchEvent(new Event("change", { bubbles: true })));
    await act(async () => container?.querySelector<HTMLFormElement>("form")?.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    ));
    await vi.waitFor(() => expect(calls.filter((call) => call.method === "POST")).toHaveLength(3));
    expect(container?.querySelector("[data-testid='location']")?.textContent).toBe(paths.retainedIntake(CASE_A));
    expect(container?.textContent).toContain("synthetic-package.pdf");

    const casesLink = Array.from(container?.querySelectorAll<HTMLAnchorElement>("a") ?? [])
      .find((link) => link.getAttribute("href") === paths.cases);
    await act(async () => casesLink?.click());
    expect(container?.querySelector("[data-testid='location']")?.textContent).toBe(paths.cases);
    const intakeLink = Array.from(container?.querySelectorAll<HTMLAnchorElement>("a") ?? [])
      .find((link) => link.textContent === "New onboarding");
    expect(intakeLink?.getAttribute("href")).toBe(paths.retainedIntake(CASE_A));
    await act(async () => intakeLink?.click());
    expect(container?.textContent).toContain("synthetic-package.pdf");
    expect(calls.filter((call) => call.method === "POST" && call.url.endsWith("/cases"))).toHaveLength(1);
    expect(calls.filter((call) => call.method === "POST" && call.url.endsWith("/intake/documents"))).toHaveLength(1);
    expect(calls.filter((call) => call.method === "POST" && call.url.endsWith("/intake/complete"))).toHaveLength(1);
  });

  it("contains a stale create after an explicit fresh start", async () => {
    const pendingCreate = deferred<Response>();
    const calls: Array<{ url: string; method: string }> = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      calls.push({ url, method });
      if (url.endsWith("/api/system/execution-profile")) return unavailable();
      if (url.endsWith("/api/clm/zero-touch/cases") && method === "POST") return pendingCreate.promise;
      return unavailable();
    });
    await act(async () => root?.render(
      <MemoryRouter initialEntries={[paths.newOnboarding]}>
        <QueryClientProvider client={testClient()}><IntakeRaceHarness /></QueryClientProvider>
      </MemoryRouter>,
    ));
    await selectIntakeFileAndSubmit("stale-create.pdf");
    await vi.waitFor(() => expect(calls.filter((call) => call.method === "POST" && call.url.endsWith("/cases"))).toHaveLength(1));
    await startFreshFromNewerJourney();

    await act(async () => {
      pendingCreate.resolve(json(summaryFixture(CASE_A, "STALE CREATE A"), 201));
      await pendingCreate.promise;
      await Promise.resolve();
    });
    expect(container?.querySelector("[data-testid='location']")?.textContent).toBe(paths.newOnboarding);
    expect(container?.textContent).toContain("Start onboarding");
    expect(container?.textContent).not.toContain("STALE CREATE A");
    expect(container?.textContent).not.toContain("stale-create.pdf");
    expect(calls.filter((call) => call.method === "POST" && call.url.includes("/intake/"))).toHaveLength(0);
  });

  it("contains a stale upload after an explicit fresh start", async () => {
    const pendingUpload = deferred<Response>();
    const calls: Array<{ url: string; method: string }> = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      calls.push({ url, method });
      if (url.endsWith("/api/system/execution-profile")) return unavailable();
      if (url.endsWith("/api/clm/zero-touch/cases") && method === "POST") return json(summaryFixture(CASE_A), 201);
      if (url.endsWith(`/${CASE_A}/intake/documents`) && method === "POST") return pendingUpload.promise;
      return unavailable();
    });
    await act(async () => root?.render(
      <MemoryRouter initialEntries={[paths.newOnboarding]}>
        <QueryClientProvider client={testClient()}><IntakeRaceHarness /></QueryClientProvider>
      </MemoryRouter>,
    ));
    await selectIntakeFileAndSubmit("stale-upload.pdf");
    await vi.waitFor(() => expect(calls.filter((call) => call.url.endsWith("/intake/documents"))).toHaveLength(1));
    await startFreshFromNewerJourney();

    await act(async () => {
      pendingUpload.resolve(json(documentFixture(CASE_A), 201));
      await pendingUpload.promise;
      await Promise.resolve();
    });
    expect(container?.querySelector("[data-testid='location']")?.textContent).toBe(paths.newOnboarding);
    expect(container?.textContent).not.toContain("stale-upload.pdf");
    expect(calls.filter((call) => call.url.endsWith("/intake/documents"))).toHaveLength(1);
    expect(calls.filter((call) => call.url.endsWith("/intake/complete"))).toHaveLength(0);
  });

  it("contains a stale completion after an explicit fresh start", async () => {
    const pendingCompletion = deferred<Response>();
    const calls: Array<{ url: string; method: string }> = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      calls.push({ url, method });
      if (url.endsWith("/api/system/execution-profile")) return unavailable();
      if (url.endsWith("/api/clm/zero-touch/cases") && method === "POST") return json(summaryFixture(CASE_A), 201);
      if (url.endsWith(`/${CASE_A}/intake/documents`) && method === "POST") return json(documentFixture(CASE_A), 201);
      if (url.endsWith(`/${CASE_A}/intake/complete`) && method === "POST") return pendingCompletion.promise;
      return unavailable();
    });
    await act(async () => root?.render(
      <MemoryRouter initialEntries={[paths.newOnboarding]}>
        <QueryClientProvider client={testClient()}><IntakeRaceHarness /></QueryClientProvider>
      </MemoryRouter>,
    ));
    await selectIntakeFileAndSubmit("stale-completion.pdf");
    await vi.waitFor(() => expect(calls.filter((call) => call.url.endsWith("/intake/complete"))).toHaveLength(1));
    await startFreshFromNewerJourney();

    await act(async () => {
      pendingCompletion.resolve(json({ ...summaryFixture(CASE_A, "STALE COMPLETE A"), status: "COMPLETED" }));
      await pendingCompletion.promise;
      await Promise.resolve();
    });
    expect(container?.querySelector("[data-testid='location']")?.textContent).toBe(paths.newOnboarding);
    expect(container?.textContent).toContain("Start onboarding");
    expect(container?.textContent).not.toContain("STALE COMPLETE A");
    expect(calls.filter((call) => call.url.endsWith("/intake/complete"))).toHaveLength(1);
  });

  it("contains a stale create across logout and replacement login", async () => {
    const pendingCreate = deferred<Response>();
    const calls: Array<{ url: string; method: string }> = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      calls.push({ url, method });
      if (url.endsWith("/api/auth/me")) return json(session);
      if (url.endsWith("/api/auth/logout") && method === "POST") return new Response(null, { status: 204 });
      if (url.endsWith("/api/auth/login") && method === "POST") {
        return json({ profile: replacementActor, csrf_token: "replacement-csrf" });
      }
      if (url.endsWith("/api/system/execution-profile")) return unavailable();
      if (url.endsWith("/api/clm/zero-touch/cases") && method === "POST") return pendingCreate.promise;
      if (url.includes("/api/clm/zero-touch/dashboard")) return unavailable();
      if (url === "/api/clm/zero-touch/cases" || url.startsWith("/api/clm/zero-touch/cases?")) return json([]);
      return unavailable();
    });
    await act(async () => root?.render(
      <MemoryRouter initialEntries={[paths.newOnboarding]}>
        <AuthProvider><AuthenticatedAppBoundary /></AuthProvider>
        <LocationProbe />
      </MemoryRouter>,
    ));
    await vi.waitFor(() => expect(container?.textContent).toContain(actor.display_name));
    await selectIntakeFileAndSubmit("actor-one-create.pdf");
    await vi.waitFor(() => expect(calls.filter((call) => call.method === "POST" && call.url.endsWith("/cases"))).toHaveLength(1));
    await logoutAndLoginAsReplacement();

    await act(async () => {
      pendingCreate.resolve(json(summaryFixture(CASE_A, "ACTOR ONE PRIVATE"), 201));
      await pendingCreate.promise;
      await Promise.resolve();
    });
    expect(container?.querySelector("[data-testid='location']")?.textContent).toBe(paths.dashboard);
    expect(container?.textContent).toContain(replacementActor.display_name);
    expect(container?.textContent).not.toContain("ACTOR ONE PRIVATE");
    expect(container?.textContent).not.toContain("actor-one-create.pdf");
    expect(calls.filter((call) => call.method === "POST" && call.url.includes("/intake/"))).toHaveLength(0);
  });

  it.each(["upload", "completion"] as const)(
    "contains a stale %s across logout and replacement login",
    async (pendingStage) => {
      const pendingOperation = deferred<Response>();
      const calls: Array<{ url: string; method: string }> = [];
      vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
        const url = String(input);
        const method = (init?.method ?? "GET").toUpperCase();
        calls.push({ url, method });
        if (url.endsWith("/api/auth/me")) return json(session);
        if (url.endsWith("/api/auth/logout") && method === "POST") return new Response(null, { status: 204 });
        if (url.endsWith("/api/auth/login") && method === "POST") {
          return json({ profile: replacementActor, csrf_token: "replacement-csrf" });
        }
        if (url.endsWith("/api/system/execution-profile")) return unavailable();
        if (url.endsWith("/api/clm/zero-touch/cases") && method === "POST") {
          return json(summaryFixture(CASE_A, "ACTOR ONE PRIVATE"), 201);
        }
        if (url.endsWith(`/${CASE_A}/intake/documents`) && method === "POST") {
          return pendingStage === "upload" ? pendingOperation.promise : json(documentFixture(CASE_A), 201);
        }
        if (url.endsWith(`/${CASE_A}/intake/complete`) && method === "POST") return pendingOperation.promise;
        if (url.includes("/api/clm/zero-touch/dashboard")) return unavailable();
        if (url === "/api/clm/zero-touch/cases" || url.startsWith("/api/clm/zero-touch/cases?")) return json([]);
        return unavailable();
      });
      await act(async () => root?.render(
        <MemoryRouter initialEntries={[paths.newOnboarding]}>
          <AuthProvider><AuthenticatedAppBoundary /></AuthProvider>
          <LocationProbe />
        </MemoryRouter>,
      ));
      await vi.waitFor(() => expect(container?.textContent).toContain(actor.display_name));
      await selectIntakeFileAndSubmit(`actor-one-${pendingStage}.pdf`);
      const pendingSuffix = pendingStage === "upload" ? "/intake/documents" : "/intake/complete";
      await vi.waitFor(() => expect(calls.filter((call) => call.url.endsWith(pendingSuffix))).toHaveLength(1));
      await logoutAndLoginAsReplacement();

      await act(async () => {
        pendingOperation.resolve(
          pendingStage === "upload"
            ? json(documentFixture(CASE_A), 201)
            : json({ ...summaryFixture(CASE_A, "ACTOR ONE COMPLETE"), status: "COMPLETED" }),
        );
        await pendingOperation.promise;
        await Promise.resolve();
      });
      expect(container?.textContent).toContain(replacementActor.display_name);
      expect(container?.textContent).not.toContain("ACTOR ONE PRIVATE");
      expect(container?.textContent).not.toContain("ACTOR ONE COMPLETE");
      expect(container?.textContent).not.toContain(`actor-one-${pendingStage}.pdf`);
      expect(calls.filter((call) => call.url.endsWith("/intake/documents"))).toHaveLength(1);
      expect(calls.filter((call) => call.url.endsWith("/intake/complete"))).toHaveLength(pendingStage === "completion" ? 1 : 0);
    },
  );

  it("P15C-NAV-12 reads retained backend state after refresh and never restores or retries File objects", async () => {
    const calls: Array<{ url: string; method: string }> = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      const method = (init?.method ?? "GET").toUpperCase();
      calls.push({ url, method });
      if (url.endsWith(`/api/clm/zero-touch/cases/${CASE_A}`)) {
        return json({ ...summaryFixture(CASE_A), status: "WAITING_FOR_REVIEW" });
      }
      if (url.endsWith(`/api/onboarding/cases/${CASE_A}/documents`)) return json([documentFixture(CASE_A)]);
      return unavailable();
    });
    await act(async () => root?.render(
      <MemoryRouter initialEntries={[paths.retainedIntake(CASE_A)]}>
        <QueryClientProvider client={testClient()}>
          <RetainedIntakeRecovery actor={actor} caseId={CASE_A} onStartFresh={() => undefined} />
        </QueryClientProvider>
      </MemoryRouter>,
    ));
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 0)); });
    expect(container?.textContent).toContain("WAITING FOR REVIEW");
    expect(container?.textContent).toContain("retained-package.pdf");
    expect(container?.textContent).toContain("Browser-selected files cannot be restored");
    expect(container?.textContent).toContain("does not retry or reconstruct");
    expect(calls).toHaveLength(2);
    expect(calls.every((call) => call.method === "GET")).toBe(true);
  });

  it("P15C-NAV-13 mounts and traverses every route without an unsafe request", async () => {
    const calls: Array<{ url: string; method: string }> = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      calls.push({ url: String(input), method: (init?.method ?? "GET").toUpperCase() });
      return unavailable();
    });
    const entries = [
      paths.root, paths.dashboard, paths.newOnboarding, paths.retainedIntake(CASE_A),
      paths.cases, paths.caseDetail(CASE_A), paths.onboarded, paths.onboardedDetail(CASE_A),
      paths.audit, paths.auditCase(CASE_A), paths.policy, paths.adminUsers, paths.adminTeams,
      paths.goldtierSandbox,
      "/unknown",
    ];
    for (const path of entries) {
      const host = document.createElement("div");
      document.body.append(host);
      const routeRoot = createRoot(host);
      await act(async () => {
        routeRoot.render(
          <MemoryRouter initialEntries={[path]}>
            <QueryClientProvider client={testClient()}>
              <App actor={allCapabilitiesActor} onLogout={() => undefined} />
            </QueryClientProvider>
          </MemoryRouter>,
        );
        await Promise.resolve();
      });
      await act(async () => routeRoot.unmount());
      host.remove();
    }
    expect(calls.filter((call) => !["GET", "HEAD", "OPTIONS"].includes(call.method))).toEqual([]);
    expect(calls.some((call) => call.url.includes("/resume"))).toBe(false);
    expect(calls.some((call) => call.url.includes("/resolve"))).toBe(false);
    expect(calls.some((call) => call.url.includes("/intake/"))).toBe(false);
  });

  it("P15C-NAV-14 makes the audit URL the only case-filter identity and Clear changes the URL", async () => {
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/api/clm/zero-touch/activity")) {
        return json({
          items: [{
          sequence: 1,
          event_type: "ONBOARDING_CREATED",
          status: "PENDING_INPUTS",
          stage: "DOCUMENT",
          outcome: "SUCCEEDED",
          timestamp: NOW,
          case_id: CASE_A,
          code: null,
          message: "Synthetic case created.",
          current_priority: null,
          current_client_scope_label: "Alpha",
          }],
          offset: 0,
          limit: 50,
          has_more: false,
        });
      }
      return unavailable();
    });
    function AuditCaseRoute() {
      return <AuditTrail actor={relationshipActor} caseId={useParams().caseId} />;
    }
    function AuditRoutes() {
      return <><Routes><Route path={routePatterns.audit} element={<AuditTrail actor={relationshipActor} caseId={null} />} /><Route path={routePatterns.auditCase} element={<AuditCaseRoute />} /></Routes><LocationProbe /></>;
    }
    await act(async () => root?.render(
      <MemoryRouter initialEntries={[paths.auditCase(CASE_A)]}>
        <QueryClientProvider client={testClient()}><AuditRoutes /></QueryClientProvider>
      </MemoryRouter>,
    ));
    await vi.waitFor(() => expect(container?.textContent).toContain(`for case ${CASE_A}`));
    const clear = Array.from(container?.querySelectorAll<HTMLAnchorElement>("a") ?? [])
      .find((link) => link.textContent?.includes("Clear case filter"));
    expect(clear?.getAttribute("href")).toBe(paths.audit);
    await act(async () => clear?.click());
    expect(container?.querySelector("[data-testid='location']")?.textContent).toBe(paths.audit);
    await vi.waitFor(() => expect(request.mock.calls.some(([url]) => String(url) === "/api/clm/zero-touch/activity")).toBe(true));
  });

  it("P15C-NAV-15 preserves user/team/filter query identity and nested-route API paths", async () => {
    expect(caseQueryKeys.dashboard("director", "TEAM_A")).not.toEqual(caseQueryKeys.dashboard("director", "TEAM_B"));
    expect(caseQueryKeys.dashboard("director", "TEAM_A")).not.toEqual(caseQueryKeys.dashboard("other", "TEAM_A"));
    expect(caseQueryKeys.caseList("director", undefined, "all", "highest_first", "TEAM_A"))
      .not.toEqual(caseQueryKeys.caseList("director", undefined, "all", "highest_first", "TEAM_B"));

    window.history.pushState({}, "", paths.caseDetail(CASE_A));
    const request = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(json([]))
      .mockResolvedValueOnce(json({}))
      .mockResolvedValueOnce(json(summaryFixture(CASE_A)));
    await fetchZeroTouchCases(undefined, "all", "highest_first", "TEAM_A");
    await fetchDashboard("TEAM_A");
    await fetchZeroTouchCase(CASE_A);
    expect(request.mock.calls.map(([url]) => String(url))).toEqual([
      "/api/clm/zero-touch/cases?team_filter=TEAM_A",
      "/api/clm/zero-touch/dashboard?team_filter=TEAM_A",
      `/api/clm/zero-touch/cases/${CASE_A}`,
    ]);
  });

  it("P15C-NAV-16 keeps API/static namespaces outside the application route table", () => {
    expect(Object.values(routePatterns).every((path) => !path.startsWith("/api") && !path.startsWith("/assets"))).toBe(true);
    expect(requiredCapabilityForPath("/api/does-not-exist")).toBeNull();
    expect(requiredCapabilityForPath("/assets/does-not-exist.js")).toBeNull();
    expect(requiredCapabilityForPath(paths.caseDetail(CASE_A))).toBe("CASE_ACCESS");
  });
});


it("does not apply a deferred A processing-focus action to the routed B case", async () => {
  const queryClient = testClient();
  seedCaseDetail(queryClient, CASE_A, "CASE A");
  seedCaseDetail(queryClient, CASE_B, "CASE B");
  const value = caseDetailFixture(CASE_A, "CASE A");
  value.processing_pipeline = [{ node_id: "DOCUMENT_IDP", label: "Documents review",
    status: "REVIEW_REQUIRED", children: [] }];
  queryClient.setQueryData(caseQueryKeys.detail(relationshipActor.user_id, CASE_A), value);
  const callbacks: (() => void)[] = [];
  vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
    callbacks.push(() => callback(0)); return 0;
  });
  await act(async () => root?.render(
    <MemoryRouter initialEntries={[paths.caseDetail(CASE_A)]}>
      <QueryClientProvider client={queryClient}>
        <CaseDetailRouteHarness onBack={() => undefined} />
      </QueryClientProvider>
    </MemoryRouter>,
  ));
  const focusAction = container?.querySelector<HTMLButtonElement>(".onboarding-progress__stages button");
  expect(focusAction).toBeTruthy();
  await act(async () => focusAction?.click());
  expect(callbacks).toHaveLength(1);
  const openB = [...container!.querySelectorAll<HTMLAnchorElement>("a")].find((item) => item.textContent === "Open B")!;
  await act(async () => openB.click());
  await vi.waitFor(() => expect(container?.querySelector("h1")?.textContent).toBe("CASE B"));
  const currentSection = container!.querySelector<HTMLElement>("input[data-review-field]")!;
  expect(currentSection).toBeTruthy();
  const focus = vi.spyOn(currentSection, "focus");
  await act(async () => callbacks.forEach((callback) => callback()));
  expect(focus).not.toHaveBeenCalled();
});
