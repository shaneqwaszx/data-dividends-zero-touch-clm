import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import GoldTierRequestPreview from "./pages/GoldTierRequestPreview";

describe("GoldTier request preview", () => {
  it("shows bounded provenance and missing authority without transport credentials", () => {
    const markup = renderToStaticMarkup(
      <GoldTierRequestPreview preview={{
        environment: "SANDBOX",
        policy_version: 42,
        dispatch_ready: false,
        operations: [{
          operation: "SHELL",
          validation: "MISSING",
          missing_fields: ["kycCustomerType"],
          fields: [{
            target_field: "kycCustomerType",
            value: null,
            provenance: "POLICY",
            authority: "TBD_SPONSOR",
            required: true,
            missing: true,
            validation: "MISSING",
          }],
        }],
      }} />,
    );

    expect(markup).toContain("Dispatch blocked");
    expect(markup).toContain("kycCustomerType");
    expect(markup).toContain("TBD SPONSOR");
    expect(markup).not.toContain("user_id");
  });
});
