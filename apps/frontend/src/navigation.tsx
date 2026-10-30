import type { ReactNode } from "react";
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

export const routePatterns = {
  root: "/",
  dashboard: "/dashboard",
  newOnboarding: "/new-onboarding",
  retainedIntake: "/new-onboarding/:caseId",
  cases: "/cases",
  caseDetail: "/cases/:caseId",
  onboarded: "/onboarded",
  onboardedDetail: "/onboarded/:caseId",
  audit: "/audit",
  auditCase: "/audit/:caseId",
  policy: "/policy",
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
  newOnboarding: routePatterns.newOnboarding,
  retainedIntake: (caseId: string) => buildCasePath(routePatterns.newOnboarding, caseId),
  cases: routePatterns.cases,
  caseDetail: (caseId: string) => buildCasePath(routePatterns.cases, caseId),
  onboarded: routePatterns.onboarded,
  onboardedDetail: (caseId: string) => buildCasePath(routePatterns.onboarded, caseId),
  audit: routePatterns.audit,
  auditCase: (caseId: string) => buildCasePath(routePatterns.audit, caseId),
  policy: routePatterns.policy,
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
  | "onboarded"
  | "audit"
  | "policy"
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
  { tab: "dashboard", label: "Dashboard", path: paths.dashboard, capability: "CASE_ACCESS", end: true },
  { tab: "home", label: "New onboarding", path: paths.newOnboarding, capability: "CASE_ACCESS", end: false },
  { tab: "queue", label: "Cases", path: paths.cases, capability: "CASE_ACCESS", end: false },
  { tab: "onboarded", label: "Onboarded", path: paths.onboarded, capability: "CASE_ACCESS", end: false },
  { tab: "audit", label: "Audit", path: paths.audit, capability: "CASE_ACCESS", end: false },
  { tab: "knowledge-review", label: "Knowledge Review", path: paths.knowledgeReview, capability: "KNOWLEDGE_REVIEW", end: true },
  { tab: "policy", label: "Policy", path: paths.policy, capability: "POLICY_VIEW", end: true },
  { tab: "users", label: "Users", path: paths.adminUsers, capability: "IDENTITY_ADMIN", end: true },
  { tab: "teams", label: "Teams", path: paths.adminTeams, capability: "TEAM_ADMIN", end: true },
  { tab: "goldtier-sandbox", label: "GoldTier Sandbox", path: paths.goldtierSandbox, capability: "PROVIDER_SANDBOX_TEST", end: true },
  { tab: "acra-diagnostics", label: "ACRA Diagnostics", path: paths.acraDiagnostics, capability: "PROVIDER_SANDBOX_TEST", end: true },
  { tab: "ai-models", label: "AI Models", path: paths.aiModels, capability: "MODEL_CONFIG_MANAGE", end: true },
];

const routeCapabilities: Array<{ pattern: string; capability: Capability; caseParam?: boolean }> = [
  { pattern: routePatterns.dashboard, capability: "CASE_ACCESS" },
  { pattern: routePatterns.newOnboarding, capability: "CASE_ACCESS" },
  { pattern: routePatterns.retainedIntake, capability: "CASE_ACCESS", caseParam: true },
  { pattern: routePatterns.cases, capability: "CASE_ACCESS" },
  { pattern: routePatterns.caseDetail, capability: "CASE_ACCESS", caseParam: true },
  { pattern: routePatterns.onboarded, capability: "CASE_ACCESS" },
  { pattern: routePatterns.onboardedDetail, capability: "CASE_ACCESS", caseParam: true },
  { pattern: routePatterns.audit, capability: "CASE_ACCESS" },
  { pattern: routePatterns.auditCase, capability: "CASE_ACCESS", caseParam: true },
  { pattern: routePatterns.policy, capability: "POLICY_VIEW" },
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

function NewOnboardingLanding({ retainedCaseId, render }: {
  retainedCaseId: string | null;
  render: () => ReactNode;
}) {
  return retainedCaseId
    ? <Navigate to={paths.caseDetail(retainedCaseId)} replace />
    : render();
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
      <span className="nav-brand">Autoboard</span>
      <span className="nav-sep" />
      <div className="nav-tabs">
        {navigationItems
          .filter((item) => actor.capabilities.includes(item.capability))
          .map((item) => (
            <NavLink
              key={item.tab}
              className={({ isActive }) => isActive ? "nav-tab nav-tab--active" : "nav-tab"}
              end={item.end}
              to={item.tab === "home" && retainedIntakeCaseId
                ? paths.caseDetail(retainedIntakeCaseId)
                : item.path}
            >
              {item.label}
            </NavLink>
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
  newOnboarding: (caseId: string | null) => ReactNode;
  cases: ReactNode;
  caseDetail: (caseId: string) => ReactNode;
  onboarded: ReactNode;
  onboardedDetail: (caseId: string) => ReactNode;
  audit: (caseId: string | null) => ReactNode;
  policy: ReactNode;
  adminUsers: ReactNode;
  adminTeams: ReactNode;
  goldtierSandbox: ReactNode;
  acraDiagnostics: ReactNode;
  aiModels: ReactNode;
  knowledgeReview: ReactNode;
}

export function WorkspaceRoutes({
  actor,
  retainedIntakeCaseId,
  dashboard,
  newOnboarding,
  cases,
  caseDetail,
  onboarded,
  onboardedDetail,
  audit,
  policy,
  adminUsers,
  adminTeams,
  goldtierSandbox,
  acraDiagnostics,
  aiModels,
  knowledgeReview,
}: WorkspaceRoutesProps) {
  const caseAccess = (content: ReactNode) => (
    <CapabilityRoute actor={actor} capability="CASE_ACCESS">{content}</CapabilityRoute>
  );
  return (
    <Routes>
      <Route path={routePatterns.root} element={<LandingRoute actor={actor} />} />
      <Route path={routePatterns.dashboard} element={caseAccess(dashboard)} />
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
      <Route path={routePatterns.onboarded} element={caseAccess(onboarded)} />
      <Route
        path={routePatterns.onboardedDetail}
        element={caseAccess(<CaseParamRoute actor={actor} render={onboardedDetail} />)}
      />
      <Route path={routePatterns.audit} element={caseAccess(audit(null))} />
      <Route
        path={routePatterns.auditCase}
        element={caseAccess(<CaseParamRoute actor={actor} render={(caseId) => audit(caseId)} />)}
      />
      <Route
        path={routePatterns.policy}
        element={<CapabilityRoute actor={actor} capability="POLICY_VIEW">{policy}</CapabilityRoute>}
      />
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
