// @vitest-environment jsdom

import { act, type ReactElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";

import ExternalAiNotice, {
  type ExternalAiNamed, type ExternalAiSurface, externalAiNoticeSummary, externalAiNoticeText, noticeProvider,
} from "./ExternalAiNotice";

const SURFACES: ExternalAiSurface[] = ["case", "general", "support", "try", "insights"];
const NAMED: ExternalAiNamed[] = ["anthropic", "openrouter", "either"];

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root | null = null;
let host: HTMLElement | null = null;
afterEach(() => {
  act(() => root?.unmount());
  host?.remove();
  root = null;
  host = null;
});

function mount(element: ReactElement): HTMLElement {
  host = document.createElement("div");
  document.body.appendChild(host);
  root = createRoot(host);
  act(() => root!.render(element));
  return host;
}

/** Text a sighted user sees: everything not inside a `hidden` element. */
function visibleText(node: Node): string {
  if (node.nodeType === Node.TEXT_NODE) return node.textContent ?? "";
  if (node instanceof HTMLElement && node.hidden) return "";
  return Array.from(node.childNodes).map(visibleText).join("");
}

const STATUS_FOR: Record<ExternalAiNamed, { providers: string[]; active: string | null; surfaces: Record<string, string[]> } | null> = {
  anthropic: null,
  openrouter: { providers: ["openrouter"], active: "openrouter", surfaces: { openrouter: ["case", "general", "support", "try", "insights"] } },
  either: {
    providers: ["anthropic", "openrouter"],
    active: null,
    surfaces: { anthropic: ["case", "general", "support", "try", "insights"], openrouter: ["case", "general", "support", "try", "insights"] },
  },
};
const PROVIDER_FACT: Record<ExternalAiNamed, string[]> = {
  anthropic: ["Claude (Anthropic)", "are sent to Anthropic", "even if no Claude answer is shown"],
  openrouter: ["GPT-OSS-120B (OpenRouter)", "are sent to OpenRouter", "even if no GPT-OSS-120B answer is shown"],
  either: ["are sent to Anthropic (Claude) or OpenRouter (GPT-OSS-120B)", "even if no AI answer is shown"],
};
const SENT_FACT: Record<ExternalAiSurface, string> = {
  case: "your question, this chat's earlier messages and this case's details are sent",
  general: "your question and this chat's earlier messages are sent",
  support: "your question, this chat's earlier messages and the active policy rules are sent",
  try: "the title and text of this change, the conversation's first question and this case's details are sent",
  insights: "counts and status labels from the eligible cases on this dashboard (no names, teams or case identifiers) are sent",
};

describe("ExternalAiNotice compact disclosure", () => {
  it("keeps every binding fact visible while collapsed, on every surface and for every provider", () => {
    for (const surface of SURFACES) {
      for (const named of NAMED) {
        const view = mount(<ExternalAiNotice surface={surface} id={`n-${surface}`} status={STATUS_FOR[named]} />);
        const notice = view.querySelector<HTMLElement>('[data-testid="external-ai-notice"]')!;
        expect(notice.getAttribute("data-provider")).toBe(named);
        const toggle = notice.querySelector("button")!;
        expect(toggle.getAttribute("aria-expanded")).toBe("false");
        const details = notice.querySelector<HTMLElement>('[data-testid="external-ai-notice-details"]')!;
        expect(details.hidden).toBe(true);
        const seen = visibleText(notice);
        expect(seen).toContain("External AI · synthetic data only.");
        expect(seen).toContain(SENT_FACT[surface]); // what is sent
        for (const fact of PROVIDER_FACT[named]) expect(seen).toContain(fact); // provider; sent even if refused
        expect(seen).toContain("Names and identifiers are replaced with placeholders first, but this is not complete.");
        expect(seen).toBe(`External AI · synthetic data only. ${externalAiNoticeSummary(surface, named)} Show full notice`);
        // The full text is not shown until expanded.
        expect(seen).not.toContain("Use synthetic test data only.");
        for (const claim of ["anonymi", "is redacted", "safe to enter", "stays inside", "never leaves", "not sent", "is removed automatically"]) {
          expect(seen.toLowerCase()).not.toContain(claim);
        }
        act(() => root!.unmount());
        root = null;
        host!.remove();
        host = null;
      }
    }
  });

  it("shows the full existing text unchanged after expanding, and collapses again", () => {
    for (const named of NAMED) {
      const view = mount(<ExternalAiNotice surface="case" status={STATUS_FOR[named]} />);
      const notice = view.querySelector<HTMLElement>('[data-testid="external-ai-notice"]')!;
      const toggle = notice.querySelector("button")!;
      const details = notice.querySelector<HTMLElement>('[data-testid="external-ai-notice-details"]')!;
      expect(toggle.getAttribute("aria-controls")).toBe(details.id);
      act(() => toggle.click());
      expect(toggle.getAttribute("aria-expanded")).toBe("true");
      expect(toggle.textContent).toBe("Hide full notice");
      expect(details.hidden).toBe(false);
      expect(details.textContent).toBe(externalAiNoticeText("case", named));
      // The summary stays visible when expanded.
      expect(visibleText(notice)).toContain(externalAiNoticeSummary("case", named));
      expect(visibleText(notice)).toContain(externalAiNoticeText("case", named));
      act(() => toggle.click());
      expect(toggle.getAttribute("aria-expanded")).toBe("false");
      expect(details.hidden).toBe(true);
      act(() => root!.unmount());
      root = null;
      host!.remove();
      host = null;
    }
  });

  it("is a native, focusable button that toggles from the keyboard", () => {
    const view = mount(<ExternalAiNotice surface="general" />);
    const toggle = view.querySelector("button")!;
    expect(toggle.tagName).toBe("BUTTON");
    expect(toggle.getAttribute("type")).toBe("button");
    expect(toggle.tabIndex).toBe(0);
    toggle.focus();
    expect(document.activeElement).toBe(toggle);
    // A native button activates on Enter and Space; jsdom does not synthesise that activation, so
    // the browser's activation (a click event on the focused button) is dispatched after the key.
    act(() => {
      toggle.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
      toggle.dispatchEvent(new MouseEvent("click", { bubbles: true, detail: 0 }));
    });
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    expect(document.activeElement).toBe(toggle);
    act(() => {
      toggle.dispatchEvent(new KeyboardEvent("keyup", { key: " ", bubbles: true }));
      toggle.dispatchEvent(new MouseEvent("click", { bubbles: true, detail: 0 }));
    });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
  });

  it("is collapsed in the server-rendered markup with the summary present and the full text hidden", () => {
    const html = renderToStaticMarkup(<ExternalAiNotice surface="support" id="n3" />);
    expect(html).toContain('aria-expanded="false"');
    expect(html).toContain(externalAiNoticeSummary("support").replace(/'/g, "&#x27;"));
    expect(html).toMatch(/<p class="ai-external-notice__details"[^>]*hidden=""/);
  });
});

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
      expect(text).toContain("replaced with placeholders, and restored only here (D-142)");
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
      expect(text).toContain("replaced with placeholders, and restored only here (D-142)");
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
