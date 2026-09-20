// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it } from "vitest";

import type { RegistryAcquisition, RegistryEvidenceBinding } from "../types";
import RegistryProvenancePanel from "./RegistryProvenancePanel";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const acquisition = {
  requested_identifier: "SYNTHETIC-TEST-ID",
  status: "COMPLETE",
  retrieved_at: "2026-09-20T00:00:09.123456Z",
  officers: [], ownership_parties: [], relationships: [], issues: [],
  operation_results: [
    { operation: "ENTITY_PROFILE", status: "COMPLETE", record_count: 1, error: null, provenance: { provider: "ACRA", environment: "MOCK", operation: "ENTITY_PROFILE", retrieved_at: "2026-09-20T00:00:01.123456Z", evidence_reference: "safe:entity" } },
    { operation: "OFFICERS", status: "EMPTY", record_count: 0, error: null, provenance: { provider: "ACRA", environment: "SANDBOX", operation: "OFFICERS", retrieved_at: "2026-09-20T00:00:02.654321Z", evidence_reference: "safe:officers" } },
  ],
} as RegistryAcquisition;

const binding: RegistryEvidenceBinding = {
  disposition: "CACHE_HIT",
  bound_to_case_at: "2026-09-20T00:05:00.000001Z",
  expires_at: "2026-12-19T00:00:01.123456Z",
  freshness_policy_id: "MOCK_ACRA_FIXED_90D",
  freshness_policy_version: 1,
  freshness_duration_seconds: 7776000,
  freshness_comparator: "EVALUATION_NOW_LT_EXPIRES_AT",
};

let root: Root | null = null;
let container: HTMLDivElement | null = null;
afterEach(() => { if (root) act(() => root?.unmount()); container?.remove(); root = null; container = null; });

function render(value: RegistryEvidenceBinding | null | undefined, source: RegistryAcquisition | null | undefined = acquisition) {
  container = document.createElement("div"); document.body.append(container); root = createRoot(container);
  act(() => root?.render(<RegistryProvenancePanel acquisition={source} binding={value} />));
  return container;
}

describe("RegistryProvenancePanel", () => {
  it("shows fetch/cache labels and preserves exact acquisition and binding timestamps", () => {
    const view = render(binding);
    expect(view.textContent).toContain("Reused cached snapshot");
    expect(view.textContent).toContain("CACHE_HIT");
    expect(view.textContent).toContain("2026-09-20T00:00:01.123456Z");
    expect(view.textContent).toContain("2026-09-20T00:00:02.654321Z");
    expect(view.textContent).toContain("2026-09-20T00:05:00.000001Z");
    expect(view.textContent).toContain("2026-12-19T00:00:01.123456Z");
    expect(view.textContent).toContain("7776000 seconds — 90 elapsed 24-hour periods");
    expect(view.textContent).toContain("Provisional Mock POC policy");
    expect(view.querySelector("a")).toBeNull();
    expect(view.querySelector("button")).toBeNull();
  });

  it("labels provider fetch without changing acquisition provenance", () => {
    const view = render({ ...binding, disposition: "PROVIDER_FETCH" });
    expect(view.textContent).toContain("Original provider fetch");
    expect(view.textContent).toContain("ACRA · MOCK");
    expect(view.textContent).toContain("ACRA · SANDBOX");
  });

  it.each([null, undefined])("treats %s legacy binding as unknown without cache/fetch inference", (value) => {
    const text = render(value).textContent ?? "";
    expect(text).toContain("Case evidence binding not recorded");
    expect(text).toContain("are unknown");
    expect(text).toContain("does not indicate a cache miss, disabled cache, provider fetch, freshness, or current validity");
  });

  it("does not invent source provenance when acquisition is absent", () => {
    const text = render(binding, null).textContent ?? "";
    expect(text).toContain("Registry acquisition provenance is not available");
    expect(text).not.toContain("ACRA ·");
  });
});
