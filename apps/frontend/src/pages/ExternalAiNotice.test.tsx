import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import ExternalAiNotice, { type ExternalAiSurface, externalAiNoticeText, noticeProvider } from "./ExternalAiNotice";

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

  // D-138 A1: the provider the notice names follows the service's report.
  const report = (active: string | null, providers = ["anthropic", "openrouter"]) => ({
    providers,
    active,
    surfaces: { anthropic: ["case", "general", "support", "try"], openrouter: ["case"] },
  });

  it("says the same things for OpenRouter on every surface, with its one approved endpoint", () => {
    for (const surface of SURFACES) {
      const text = externalAiNoticeText(surface, "openrouter");
      expect(text).toContain("When GPT-OSS-120B (OpenRouter) is asked");
      expect(text).toContain("are sent to OpenRouter, an external AI provider outside this application");
      expect(text).toContain("routes them to the one approved GPT-OSS-120B endpoint");
      expect(text).toContain("They are sent even if no GPT-OSS-120B answer is shown to you.");
      expect(text).toContain("Use synthetic test data only.");
      expect(text).toContain("Automatic removal covers only some known identifiers, not everything you type.");
      expect(text).not.toContain("Anthropic");
      const either = externalAiNoticeText(surface, "either");
      expect(either).toContain("Anthropic for Claude, or OpenRouter (routed to the one approved GPT-OSS-120B endpoint)");
      expect(either).toContain("They are sent even if no AI answer is shown to you.");
      for (const text2 of [text.toLowerCase(), either.toLowerCase()]) {
        for (const claim of ["anonymi", "is redacted", "safe to enter", "stays inside", "never leaves", "not sent"]) {
          expect(text2).not.toContain(claim);
        }
      }
    }
    expect(externalAiNoticeText("case", "openrouter")).toContain(
      "is asked in this chat, your question, this chat's earlier messages and this case's details are sent to OpenRouter",
    );
  });

  it("names the one provider that may serve a surface, both where both may, and Anthropic otherwise", () => {
    // QG P2-1: where both may serve, the active model never narrows it (HR can switch it).
    expect(noticeProvider("case", report("openrouter"))).toBe("either");
    expect(noticeProvider("case", report("anthropic"))).toBe("either");
    expect(noticeProvider("case", report(null))).toBe("either");
    expect(noticeProvider("case", report("openrouter", ["anthropic"]))).toBe("anthropic");
    // GPT-OSS-120B serves the case chat only.
    expect(noticeProvider("general", report("openrouter"))).toBe("anthropic");
    expect(noticeProvider("support", report("openrouter"))).toBe("anthropic");
    expect(noticeProvider("case", report(null, ["openrouter"]))).toBe("openrouter");
    // No report, a malformed one or unknown names keep the original wording.
    expect(noticeProvider("case")).toBe("anthropic");
    expect(noticeProvider("case", null)).toBe("anthropic");
    expect(noticeProvider("case", { providers: "x", active: null, surfaces: {} } as never)).toBe("anthropic");
    expect(noticeProvider("case", { providers: ["other"], active: "other", surfaces: { other: ["case"] } })).toBe("anthropic");
    expect(noticeProvider("case", { providers: [], active: null, surfaces: {} })).toBe("anthropic");
  });

  it("renders the provider it names", () => {
    const html = renderToStaticMarkup(
      <ExternalAiNotice surface="case" id="n2" status={report("openrouter", ["openrouter"])} />,
    );
    expect(html).toContain('data-provider="openrouter"');
    expect(html).toContain("<strong>External AI · synthetic data only.</strong>");
    expect(renderToStaticMarkup(<ExternalAiNotice surface="case" />)).toContain('data-provider="anthropic"');
  });
});
