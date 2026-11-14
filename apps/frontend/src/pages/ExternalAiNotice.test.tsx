import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import ExternalAiNotice, { type ExternalAiSurface, externalAiNoticeText } from "./ExternalAiNotice";

const SURFACES: ExternalAiSurface[] = ["case", "general", "support", "try", "insights"];

describe("ExternalAiNotice (P2-3)", () => {
  it("says on every surface: external processing by Anthropic, synthetic data only, no real personal data", () => {
    for (const surface of SURFACES) {
      const text = externalAiNoticeText(surface);
      expect(text).toContain("Claude (Anthropic)");
      expect(text).toContain("sent to Anthropic, an external AI provider outside this application");
      // N1: sending does not depend on a Claude answer being shown.
      expect(text).toContain("They are sent even if no Claude answer is shown to you.");
      expect(text).toContain("When Claude (Anthropic) is asked");
      expect(text).not.toContain("answers");
      expect(text).toContain("Use synthetic test data only.");
      expect(text).toContain("Do not enter real names, contact details, ID numbers or any other personal or confidential information.");
      expect(text).toContain("Automatic removal covers only some known identifiers, not everything you type.");
    }
  });

  it("never claims that personal information is removed, anonymised or kept inside the application", () => {
    for (const surface of SURFACES) {
      const text = externalAiNoticeText(surface).toLowerCase();
      for (const claim of [
        "all personal", "is removed automatically", "are removed automatically", "anonymi", "is redacted",
        "safe to enter", "stays inside", "never leaves", "not sent",
      ]) {
        expect(text).not.toContain(claim);
      }
    }
  });

  it("lists what each path sends (D-129 r3.1 sections 2A to 2D)", () => {
    expect(externalAiNoticeText("case")).toContain("in this chat, your question, this chat's earlier messages and this case's details are sent");
    expect(externalAiNoticeText("general")).toContain("in this chat, your question and this chat's earlier messages are sent");
    expect(externalAiNoticeText("support")).toContain("your question, this chat's earlier messages and the active policy rules are sent");
    expect(externalAiNoticeText("try")).toContain(
      "is asked for Try with this change, the title and text of this change, the conversation's first question and this case's details are sent",
    );
    // D-130 amendment draft (fifth path): aggregates only.
    expect(externalAiNoticeText("insights")).toContain(
      "is asked for AI insights, counts and status labels from the eligible cases on this dashboard (no names, teams or case identifiers) are sent",
    );
    // The general chat sends no case data.
    expect(externalAiNoticeText("general")).not.toContain("case");
  });

  it("renders with its id, so a question box or button can be described by it", () => {
    const html = renderToStaticMarkup(<ExternalAiNotice surface="try" id="n1" />);
    expect(html).toContain('id="n1"');
    expect(html).toContain('data-surface="try"');
    expect(html).toContain("<strong>External AI · synthetic data only.</strong>");
  });
});
