import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("App", () => {
  it("labels the application as a Phase 00 foundation", () => {
    const markup = renderToStaticMarkup(<App />);

    expect(markup).toContain("Zero-Touch Client Onboarding");
    expect(markup).toContain("Foundation ready");
    expect(markup).toContain(
      "Business workflow and external integrations are intentionally not active",
    );
  });
});
