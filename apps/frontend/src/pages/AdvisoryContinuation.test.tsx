import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { ZeroTouchCaseSummary } from "../types";
import AdvisoryContinuation from "./AdvisoryContinuation";

function markup(part: Partial<ZeroTouchCaseSummary>): string {
  return renderToStaticMarkup(
    <AdvisoryContinuation summary={part as ZeroTouchCaseSummary} disabled={false} onContinue={() => undefined} />,
  );
}

describe("D-124 advisory continuation", () => {
  it("shows nothing unless the backend offers a continuation", () => {
    expect(markup({ advisory_continuation: null })).toBe("");
  });

  it("offers the creator an explicit continuation and says nothing is sent yet", () => {
    const view = markup({ status: "WAITING_FOR_REVIEW", advisory_continuation: { can_resume: true } });
    expect(view).toContain("Continue onboarding</button>");
    expect(view).toContain("nothing is sent to GoldTier until you confirm");
  });

  it("gives other readers no action", () => {
    const view = markup({ status: "WAITING_FOR_REVIEW", advisory_continuation: { can_resume: false } });
    expect(view).not.toContain("<button");
    expect(view).toContain("created this case");
  });

  it("offers a retry after a failed continuation", () => {
    const view = markup({ status: "TECHNICAL_FAILURE", advisory_continuation: { can_resume: true } });
    expect(view).toContain("Try again</button>");
    expect(view).toContain("Nothing was sent to GoldTier");
  });
});
