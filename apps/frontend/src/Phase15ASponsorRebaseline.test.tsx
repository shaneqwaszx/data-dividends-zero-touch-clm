import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import HomeOnboarding from "./pages/HomeOnboarding";
import { RegistryStatePanel } from "./pages/CaseStatePanels";
import type { ZeroTouchCaseSummary } from "./types";

const registryStageSummary = {
  case: {},
  status: "RUNNING",
  current_stage: "REGISTRY",
  active_exceptions: [],
  technical_failure: null,
} as unknown as ZeroTouchCaseSummary;

describe("Phase 15A sponsor rebaseline copy", () => {
  it("states that the POC processes a user-supplied onboarding package", () => {
    const markup = renderToStaticMarkup(
      <HomeOnboarding
        summary={null}
        uen="202400001A"
        onUenChange={() => undefined}
        countryOfIncorporation="SG"
        onCountryChange={() => undefined}
        documentFiles={[]}
        onDocumentFilesChange={() => undefined}
        caseTeamDisplayName="Alpha Corporate Onboarding"
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
        onViewAudit={() => undefined}
      />,
    );

    expect(markup).toContain("Provide the onboarding package available to you");
    expect(markup).toContain("begins processing after the package is supplied");
  });

  it("labels the registry stage as acquisition rather than verification", () => {
    const markup = renderToStaticMarkup(<RegistryStatePanel summary={registryStageSummary} />);

    expect(markup).toContain("Registry acquisition");
    expect(markup).not.toContain("Registry verification");
  });
});
