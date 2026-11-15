import { describe, expect, it } from "vitest";
import { ledgerRefusal, type ModelConnectionTest } from "./aiAssistant";

const base: ModelConnectionTest = {
  outcome: "failed", code: "PREFLIGHT_FAILED:ledger.healthy", listed: null,
  complete_ms: null, stream_ms: null, first_piece_ms: null,
};

describe("ledgerRefusal (D-138 R4)", () => {
  it("names the spending store's own refusal behind a failed ledger.healthy check", () => {
    const test = { ...base, checks: [
      { check: "key.present", ok: true, detail: "session" },
      { check: "ledger.healthy", ok: false, detail: "refused: LEGACY_STORE" },
    ] };
    expect(ledgerRefusal(test)).toBe("LEGACY_STORE");
  });
  it("is null for a passing check, a free-text detail or no checks at all", () => {
    expect(ledgerRefusal({ ...base, checks: [{ check: "ledger.healthy", ok: true, detail: "alias key-01" }] })).toBeNull();
    expect(ledgerRefusal({ ...base, checks: [{ check: "ledger.healthy", ok: false, detail: "refused: <b>x</b>" }] })).toBeNull();
    expect(ledgerRefusal(base)).toBeNull();
    expect(ledgerRefusal(null)).toBeNull();
  });
});
