import { Fragment, type ReactNode } from "react";
import {
  Link,
  matchPath,
  Navigate,
  NavLink,
  Route,
  Routes,
  useParams,
} from "react-router";

import type { AuthenticatedProfile, Capability } from "./types";
import { canViewExecutionPlan } from "./workflowExecutionPlan";
import { workflowManagerEnabled } from "./workflowFlags";
import { WorkflowTabLinks } from "./pages/WorkflowTab";
import { sampleCaseUrlId } from "./pages/mockDashboards/onboardingSample";

export const routePatterns = {
  root: "/",
  dashboard: "/dashboard",
  gtcDashboard: "/dashboard/gtc",
  periodicReviewDashboard: "/dashboard/periodic-review",
  newOnboarding: "/new-onboarding",
  retainedIntake: "/new-onboarding/:caseId",
  cases: "/cases",
  caseDetail: "/cases/:caseId",
  onboarded: "/onboarded",
  onboardedDetail: "/onboarded/:caseId",
  audit: "/audit",
  auditCase: "/audit/:caseId",
  policy: "/policy",
  workflowDesigner: "/policy/workflow-designer",
  workflows: "/workflows",
  workflowTab: "/workflow-tabs/:workflowId",
  workflowCases: "/workflow-tabs/:workflowId/cases",
  workflowRun: "/workflow-tabs/:workflowId/runs/:runId",
  adminUsers: "/admin/users",
  adminTeams: "/admin/teams",
  goldtierSandbox: "/admin/goldtier-sandbox",
  acraDiagnostics: "/admin/acra",
  aiModels: "/admin/ai-models",
  knowledgeReview: "/knowledge-review",
} as const;

const CASE_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function parseCaseId(value: string | undefined): string | null {
  if (!value || value.length !== 36 || !CASE_ID.test(value)) return null;
  return value.toLowerCase();
}

function buildCasePath(base: string, caseId: string): string {
  const normalized = parseCaseId(caseId);
  return normalized ? `${base}/${encodeURIComponent(normalized)}` : base;
}

export const paths = {
  root: routePatterns.root,
  dashboard: routePatterns.dashboard,
  gtcDashboard: routePatterns.gtcDashboard,
  periodicReviewDashboard: routePatterns.periodicReviewDashboard,
  newOnboarding: routePatterns.newOnboarding,
  retainedIntake: (caseId: string) => buildCasePath(routePatterns.newOnboarding, caseId),
  cases: routePatterns.cases,
  caseDetail: (caseId: string) => buildCasePath(routePatterns.cases, caseId),
  /** Read-only case page for a fixed dashboard sample case such as `sample-0041`. */
  sampleCaseDetail: (sampleCaseId: string) => {
    const urlId = sampleCaseUrlId(sampleCaseId);
    return urlId ? buildCasePath(routePatterns.cases, urlId) : routePatterns.cases;
  },
  audit: routePatterns.audit,
  auditCase: (caseId: string) => buildCasePath(routePatterns.audit, caseId),
  policy: routePatterns.policy,
  workflowDesigner: routePatterns.workflowDesigner,
  workflows: routePatterns.workflows,
  workflowTab: (workflowId: string) => `/workflow-tabs/${encodeURIComponent(workflowId)}`,
  workflowCases: (workflowId: string) => `/workflow-tabs/${encodeURIComponent(workflowId)}/cases`,
  workflowRun: (workflowId: string, runId: string) => `/workflow-tabs/${encodeURIComponent(workflowId)}/runs/${encodeURIComponent(runId)}`,
  adminUsers: routePatterns.adminUsers,
  adminTeams: routePatterns.adminTeams,
  goldtierSandbox: routePatterns.goldtierSandbox,
  acraDiagnostics: routePatterns.acraDiagnostics,
  aiModels: routePatterns.aiModels,
  knowledgeReview: routePatterns.knowledgeReview,
} as const;

export type AppTab =
  | "dashboard"
  | "home"
  | "queue"
  | "audit"
  | "policy"
  | "workflows"
  | "users"
  | "teams"
  | "goldtier-sandbox"
  | "acra-diagnostics"
  | "ai-models"
  | "knowledge-review";

interface NavigationItem {
  tab: AppTab;
  label: string;
  path: string;
  capability: Capability;
  end: boolean;
}

const navigationItems: NavigationItem[] = [
  { tab: "dashboard", label: "Dashboard", path: paths.dashboard, capability: "CASE_ACCESS", end: false },
  { tab: "home", label: "New onboarding", path: paths.newOnboarding, capability: "CASE_ACCESS", end: false },
  { tab: "queue", label: "Cases", path: paths.cases, capability: "CASE_ACCESS", end: false },
  { tab: "audit", label: "Audit", path: paths.audit, capability: "CASE_ACCESS", end: false },
  { tab: "knowledge-review", label: "Knowledge Review", path: paths.knowledgeReview, capability: "KNOWLEDGE_REVIEW", end: true },
  { tab: "policy", label: "Policy", path: paths.policy, capability: "POLICY_VIEW", end: true },
  { tab: "workflows", label: "Workflows", path: paths.workflows, capability: "POLICY_APPROVE", end: true },
  { tab: "users", label: "Users", path: paths.adminUsers, capability: "IDENTITY_ADMIN", end: true },
  { tab: "teams", label: "Teams", path: paths.adminTeams, capability: "TEAM_ADMIN", end: true },
  { tab: "goldtier-sandbox", label: "GoldTier Sandbox", path: paths.goldtierSandbox, capability: "PROVIDER_SANDBOX_TEST", end: true },
  { tab: "acra-diagnostics", label: "ACRA Diagnostics", path: paths.acraDiagnostics, capability: "PROVIDER_SANDBOX_TEST", end: true },
  { tab: "ai-models", label: "AI Models", path: paths.aiModels, capability: "MODEL_CONFIG_MANAGE", end: true },
];

const routeCapabilities: Array<{ pattern: string; capability: Capability; caseParam?: boolean }> = [
  { pattern: routePatterns.dashboard, capability: "CASE_ACCESS" },
  { pattern: routePatterns.gtcDashboard, capability: "CASE_ACCESS" },
  { pattern: routePatterns.periodicReviewDashboard, capability: "CASE_ACCESS" },
  { pattern: routePatterns.newOnboarding, capability: "CASE_ACCESS" },
  { pattern: routePatterns.retainedIntake, capability: "CASE_ACCESS", caseParam: true },
  { pattern: routePatterns.cases, capability: "CASE_ACCESS" },
  { pattern: routePatterns.caseDetail, capability: "CASE_ACCESS", caseParam: true },
  { pattern: routePatterns.onboarded, capability: "CASE_ACCESS" },
  { pattern: routePatterns.onboardedDetail, capability: "CASE_ACCESS", caseParam: true },
  { pattern: routePatterns.audit, capability: "CASE_ACCESS" },
  { pattern: routePatterns.auditCase, capability: "CASE_ACCESS", caseParam: true },
  { pattern: routePatterns.policy, capability: "POLICY_VIEW" },
  // The page shows HR and Directors the plan; the backend refuses every other role.
  { pattern: routePatterns.workflowDesigner, capability: "POLICY_VIEW" },
  { pattern: routePatterns.workflows, capability: "POLICY_APPROVE" },
  { pattern: routePatterns.workflowTab, capability: "CASE_ACCESS" },
  { pattern: routePatterns.workflowCases, capability: "CASE_ACCESS" },
  { pattern: routePatterns.workflowRun, capability: "CASE_ACCESS" },
  { pattern: routePatterns.adminUsers, capability: "IDENTITY_ADMIN" },
  { pattern: routePatterns.adminTeams, capability: "TEAM_ADMIN" },
  { pattern: routePatterns.goldtierSandbox, capability: "PROVIDER_SANDBOX_TEST" },
  { pattern: routePatterns.acraDiagnostics, capability: "PROVIDER_SANDBOX_TEST" },
  { pattern: routePatterns.aiModels, capability: "MODEL_CONFIG_MANAGE" },
  { pattern: routePatterns.knowledgeReview, capability: "KNOWLEDGE_REVIEW" },
];

export function requiredCapabilityForPath(pathname: string): Capability | null {
  for (const route of routeCapabilities) {
    const match = matchPath({ path: route.pattern, end: true }, pathname);
    if (match && (!route.caseParam || parseCaseId(match.params.caseId))) {
      return route.capability;
    }
  }
  return null;
}

export function defaultPathForProfile(actor: AuthenticatedProfile): string | null {
  if (actor.capabilities.includes("CASE_ACCESS")) return paths.dashboard;
  if (actor.capabilities.includes("IDENTITY_ADMIN")) return paths.adminUsers;
  if (actor.capabilities.includes("TEAM_ADMIN")) return paths.adminTeams;
  if (actor.capabilities.includes("PROVIDER_SANDBOX_TEST")) return paths.goldtierSandbox;
  if (actor.capabilities.includes("KNOWLEDGE_REVIEW")) return paths.knowledgeReview;
  if (actor.capabilities.includes("POLICY_VIEW")) return paths.policy;
  return null;
}

export function UnavailableRoute({ actor }: { actor: AuthenticatedProfile }) {
  const destination = defaultPathForProfile(actor);
  return (
    <section className="ds-root ds-page" aria-labelledby="route-unavailable-heading">
      <h1 id="route-unavailable-heading">Page unavailable</h1>
      <p className="text-muted">
        This page is not available for the current workspace.
      </p>
      {destination && <Link className="btn btn-secondary" to={destination}>Return to workspace</Link>}
    </section>
  );
}

function CapabilityRoute({
  actor,
  capability,
  children,
}: {
  actor: AuthenticatedProfile;
  capability: Capability;
  children: ReactNode;
}) {
  return actor.capabilities.includes(capability)
    ? children
    : <UnavailableRoute actor={actor} />;
}

/** Policy & Workflow sub-tabs, shown only to HR and Directors (cosmetic; backend decides). */
function PolicySectionTabs() {
  const tab = ({ isActive }: { isActive: boolean }) => `btn ${isActive ? "btn-primary" : "btn-secondary"}`;
  return (
    <nav className="ds-root policy-section-tabs" aria-label="Policy and Workflow">
      <NavLink to={paths.policy} end className={tab}>Policy rules</NavLink>
      <NavLink to={paths.workflowDesigner} end className={tab}>Workflow designer</NavLink>
    </nav>
  );
}

function LandingRoute({ actor }: { actor: AuthenticatedProfile }) {
  const destination = defaultPathForProfile(actor);
  return destination
    ? <Navigate to={destination} replace />
    : <UnavailableRoute actor={actor} />;
}

function CaseParamRoute({
  actor,
  render,
}: {
  actor: AuthenticatedProfile;
  render: (caseId: string) => ReactNode;
}) {
  const caseId = parseCaseId(useParams().caseId);
  return caseId ? render(caseId) : <UnavailableRoute actor={actor} />;
}

function WorkflowTabRoute({ render }: { render?: (workflowId: string) => ReactNode }) {
  const { workflowId } = useParams();
  return workflowId && render ? render(workflowId) : null;
}

function WorkflowRunRoute({ render }: { render?: (workflowId: string, runId: string) => ReactNode }) {
  const { workflowId, runId } = useParams();
  return workflowId && runId && render ? render(workflowId, runId) : null;
}

function NewOnboardingLanding({ retainedCaseId, render }: {
  retainedCaseId: string | null;
  render: () => ReactNode;
}) {
  return retainedCaseId
    ? <Navigate to={paths.caseDetail(retainedCaseId)} replace />
    : render();
}

/** The brand returns to the profile's own landing page; plain text when there is none. */
function BrandHome({ actor }: { actor: AuthenticatedProfile }) {
  const destination = defaultPathForProfile(actor);
  return destination
    ? <Link className="nav-brand" to={destination} aria-label="Autoboard home">Autoboard</Link>
    : <span className="nav-brand">Autoboard</span>;
}

export function WorkspaceTabs({
  actor,
  retainedIntakeCaseId,
  trailing,
}: {
  actor: AuthenticatedProfile;
  retainedIntakeCaseId?: string | null;
  trailing?: ReactNode;
}) {
  return (
    <nav className="ds-root nav" aria-label="Main workspace">
      <BrandHome actor={actor} />
      <span className="nav-sep" />
      <div className="nav-tabs">
        {navigationItems
          .filter(item => item.tab !== "workflows" || workflowManagerEnabled())
          .filter((item) => actor.capabilities.includes(item.capability))
          .map((item) => (
            <Fragment key={item.tab}>
              <NavLink
                className={({ isActive }) => isActive ? "nav-tab nav-tab--active" : "nav-tab"}
                end={item.end}
                to={item.tab === "home" && retainedIntakeCaseId
                  ? paths.caseDetail(retainedIntakeCaseId)
                  : item.path}
              >
                {item.label}
              </NavLink>
              {item.tab === "home" && workflowManagerEnabled() && <WorkflowTabLinks actor={actor} />}
            </Fragment>
          ))}
      </div>
      {trailing && <div className="nav-meta">{trailing}</div>}
    </nav>
  );
}

export interface WorkspaceRoutesProps {
  actor: AuthenticatedProfile;
  retainedIntakeCaseId: string | null;
  dashboard: ReactNode;
  gtcDashboard: ReactNode;
  periodicReviewDashboard: ReactNode;
  newOnboarding: (caseId: string | null) => ReactNode;
  cases: ReactNode;
  caseDetail: (caseId: string) => ReactNode;
  audit: (caseId: string | null) => ReactNode;
  policy: ReactNode;
  workflowDesigner?: ReactNode;
  adminUsers: ReactNode;
  adminTeams: ReactNode;
  goldtierSandbox: ReactNode;
  acraDiagnostics: ReactNode;
  aiModels: ReactNode;
  workflows?: ReactNode;
  workflowTab?: (workflowId: string) => ReactNode;
  workflowCases?: (workflowId: string) => ReactNode;
  workflowRun?: (workflowId: string, runId: string) => ReactNode;
  knowledgeReview: ReactNode;
}

export function WorkspaceRoutes({
  actor,
  retainedIntakeCaseId,
  dashboard,
  gtcDashboard,
  periodicReviewDashboard,
  newOnboarding,
  cases,
  caseDetail,
  audit,
  policy,
  workflowDesigner,
  adminUsers,
  adminTeams,
  goldtierSandbox,
  acraDiagnostics,
  aiModels,
  workflows,
  workflowTab,
  workflowCases,
  workflowRun,
  knowledgeReview,
}: WorkspaceRoutesProps) {
  const caseAccess = (content: ReactNode) => (
    <CapabilityRoute actor={actor} capability="CASE_ACCESS">{content}</CapabilityRoute>
  );
  const policySection = (content: ReactNode) => (
    <CapabilityRoute actor={actor} capability="POLICY_VIEW">
      {workflowDesigner && canViewExecutionPlan(actor) && <PolicySectionTabs />}
      {content}
    </CapabilityRoute>
  );
  return (
    <Routes>
      <Route path={routePatterns.root} element={<LandingRoute actor={actor} />} />
      <Route path={routePatterns.dashboard} element={caseAccess(dashboard)} />
      <Route path={routePatterns.gtcDashboard} element={caseAccess(gtcDashboard)} />
      <Route path={routePatterns.periodicReviewDashboard} element={caseAccess(periodicReviewDashboard)} />
      <Route
        path={routePatterns.newOnboarding}
        element={caseAccess(
          <NewOnboardingLanding
            retainedCaseId={retainedIntakeCaseId}
            render={() => newOnboarding(null)}
          />,
        )}
      />
      <Route
        path={routePatterns.retainedIntake}
        element={caseAccess(<CaseParamRoute actor={actor} render={(caseId) => newOnboarding(caseId)} />)}
      />
      <Route path={routePatterns.cases} element={caseAccess(cases)} />
      <Route
        path={routePatterns.caseDetail}
        element={caseAccess(<CaseParamRoute actor={actor} render={caseDetail} />)}
      />
      {/* The Onboarded pages were folded into Cases (its "Onboarded" view); old links redirect. */}
      <Route path={routePatterns.onboarded} element={caseAccess(<Navigate to={paths.cases} replace />)} />
      <Route
        path={routePatterns.onboardedDetail}
        element={caseAccess(<CaseParamRoute actor={actor} render={(caseId) => <Navigate to={paths.caseDetail(caseId)} replace />} />)}
      />
      <Route path={routePatterns.audit} element={caseAccess(audit(null))} />
      <Route
        path={routePatterns.auditCase}
        element={caseAccess(<CaseParamRoute actor={actor} render={(caseId) => audit(caseId)} />)}
      />
      <Route path={routePatterns.policy} element={policySection(policy)} />
      {workflowDesigner && (
        <Route path={routePatterns.workflowDesigner} element={policySection(workflowDesigner)} />
      )}
      <Route
        path={routePatterns.adminUsers}
        element={<CapabilityRoute actor={actor} capability="IDENTITY_ADMIN">{adminUsers}</CapabilityRoute>}
      />
      <Route
        path={routePatterns.adminTeams}
        element={<CapabilityRoute actor={actor} capability="TEAM_ADMIN">{adminTeams}</CapabilityRoute>}
      />
      <Route
        path={routePatterns.goldtierSandbox}
        element={<CapabilityRoute actor={actor} capability="PROVIDER_SANDBOX_TEST">{goldtierSandbox}</CapabilityRoute>}
      />
      <Route
        path={routePatterns.acraDiagnostics}
        element={<CapabilityRoute actor={actor} capability="PROVIDER_SANDBOX_TEST">{acraDiagnostics}</CapabilityRoute>}
      />
      <Route path={routePatterns.workflowTab} element={caseAccess(<WorkflowTabRoute render={workflowTab} />)} />
      <Route path={routePatterns.workflowCases} element={caseAccess(<WorkflowTabRoute render={workflowCases} />)} />
      <Route path={routePatterns.workflowRun} element={caseAccess(<WorkflowRunRoute render={workflowRun} />)} />
      <Route
        path={routePatterns.workflows}
        element={<CapabilityRoute actor={actor} capability="POLICY_APPROVE">{workflows}</CapabilityRoute>}
      />
      <Route
        path={routePatterns.aiModels}
        element={<CapabilityRoute actor={actor} capability="MODEL_CONFIG_MANAGE">{aiModels}</CapabilityRoute>}
      />
      <Route
        path={routePatterns.knowledgeReview}
        element={<CapabilityRoute actor={actor} capability="KNOWLEDGE_REVIEW">{knowledgeReview}</CapabilityRoute>}
      />
      <Route path="*" element={<UnavailableRoute actor={actor} />} />
    </Routes>
  );
}
