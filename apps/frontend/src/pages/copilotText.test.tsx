// @vitest-environment jsdom

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { CopilotText } from "./copilotText";

describe("CopilotText", () => {
  it("shows bold and bullets as formatting instead of stars", () => {
    const html = renderToStaticMarkup(
      <CopilotText text={"You need to **upload documents**.\n\n**What to do:**\n- Open *Document Verification*.\n- Upload them."} />,
    );

    expect(html).toContain("<strong>upload documents</strong>");
    expect(html).toContain("<ul><li>Open Document Verification.</li><li>Upload them.</li></ul>");
    expect(html).not.toContain("*");
  });

  it("keeps numbered lists and never renders model text as HTML", () => {
    const html = renderToStaticMarkup(
      <CopilotText text={"1. First <b>x</b>\n2. Second"} />,
    );

    expect(html).toContain("<ol><li>First &lt;b&gt;x&lt;/b&gt;</li><li>Second</li></ol>");
  });
});
