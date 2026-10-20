// @vitest-environment jsdom

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AiAssistantText } from "./aiAssistantText";

describe("AiAssistantText", () => {
  it("shows bold and bullets as formatting instead of stars", () => {
    const html = renderToStaticMarkup(
      <AiAssistantText text={"You need to **upload documents**.\n\n**What to do:**\n- Open *Document Verification*.\n- Upload them."} />,
    );

    expect(html).toContain("<strong>upload documents</strong>");
    expect(html).toContain("<ul><li>Open Document Verification.</li><li>Upload them.</li></ul>");
    expect(html).not.toContain("*");
  });

  it("keeps numbered lists and never renders model text as HTML", () => {
    const html = renderToStaticMarkup(
      <AiAssistantText text={"1. First <b>x</b>\n2. Second"} />,
    );

    expect(html).toContain("<ol><li>First &lt;b&gt;x&lt;/b&gt;</li><li>Second</li></ol>");
  });

  it("keeps counting when an explanation sits between numbered steps", () => {
    const indented = renderToStaticMarkup(
      <AiAssistantText text={"Two things are missing:\n\n1. **Address decision**\n\n   The document differs from ACRA.\n\n2. **Ownership evidence**\n\n   Upload a register."} />,
    );
    expect(indented).toContain(
      '<ol><li>Address decision<p class="ai-assistant-item-detail">The document differs from ACRA.</p></li><li>Ownership evidence<p class="ai-assistant-item-detail">Upload a register.</p></li></ol>'
        .replace("Address decision", "<strong>Address decision</strong>")
        .replace("Ownership evidence", "<strong>Ownership evidence</strong>"),
    );

    const flat = renderToStaticMarkup(<AiAssistantText text={"1. First\n\nWhy it matters.\n\n2. Second"} />);
    expect(flat).toContain('<ol start="2"><li>Second</li></ol>');
  });
});
