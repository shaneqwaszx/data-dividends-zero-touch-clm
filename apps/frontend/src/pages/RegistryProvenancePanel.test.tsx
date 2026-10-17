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
  it("distinguishes approved local seed evidence from configured Marketplace", () => {
    const text = render({ ...binding, synthetic_seed_namespace: "LOCAL_SYNTHETIC_UAT_V1" }).textContent;
    expect(text).toContain("Local Synthetic Seed");
    expect(text).toContain("LOCAL PROJECT SYNTHETIC MOCK");
    expect(text).toContain("LOCAL_SYNTHETIC_UAT_V1");
    expect(text).toContain("CACHE_HIT");
    expect(text).toContain("configured provider is unchanged");
  });
  it("does not infer local seed classification from an ordinary Mock cache hit", () => {
    expect(render(binding).textContent).not.toContain("Local Synthetic Seed");
  });
  it("explains explicit empty ownership separately from retrieved identity and request failures", () => {
    const source: RegistryAcquisition = { ...acquisition, operation_results: [
      acquisition.operation_results[0],
      { ...acquisition.operation_results[1], operation: "OWNERSHIP_PARTIES", status: "EMPTY", provenance: { ...acquisition.operation_results[0].provenance!, operation: "OWNERSHIP_PARTIES" } },
    ] };
    const text = render(null, source).textContent ?? "";
    expect(text).toContain("Identity retrieved");
    expect(text).toContain("Ownership unavailable from current registry evidence");
    expect(text).not.toContain("Ownership retrieval failed");
  });

  it.each(["FAILED", "NOT_ATTEMPTED"] as const)("does not label %s ownership as an explicit empty success", (status) => {
    const source: RegistryAcquisition = { ...acquisition, operation_results: [
      acquisition.operation_results[0], { ...acquisition.operation_results[1], operation: "OWNERSHIP_PARTIES", status },
    ] };
    expect(render(null, source).textContent).not.toContain("Ownership unavailable from current registry evidence");
  });

  it("shows fetch/cache labels and preserves exact acquisition and binding timestamps", () => {
    const view = render(binding);
    expect(view.textContent).toContain("Reused fresh registry evidence — no ACRA request required.");
    expect(view.textContent).toContain("CACHE_HIT");
    expect(view.textContent).toContain("2026-09-20T00:00:01.123456Z");
    expect(view.textContent).toContain("2026-09-20T00:00:02.654321Z");
    expect(view.textContent).toContain("2026-09-20T00:05:00.000001Z");
    expect(view.textContent).toContain("2026-12-19T00:00:01.123456Z");
    expect(view.textContent).toContain("7776000 seconds");
    expect(view.textContent).toContain("Provisional Mock POC policy");
    expect(view.textContent).toContain("EVALUATION_NOW_LT_EXPIRES_AT");
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

it.each(["API_MARKETPLACE_MOCK", "API_MARKETPLACE_PROTOCOL_TEST"] as const)(
  "explains partnership authority for %s without implying technical failure", (providerMode) => {
    const source: RegistryAcquisition = { ...acquisition, status: "PARTIAL", operation_results: [
      acquisition.operation_results[0],
      { operation: "OWNERSHIP_PARTIES", status: "UNSUPPORTED", record_count: 0, error: null, provenance: null },
    ] };
    container = document.createElement("div"); document.body.append(container); root = createRoot(container);
    act(() => root?.render(<RegistryProvenancePanel acquisition={source} binding={null}
      entityType="PARTNERSHIP" providerMode={providerMode} />));
    const text = container.textContent ?? "";
    expect(text).toContain("not an authoritative partnership-ownership source");
    expect(text).toContain("Reviewed supplementary ownership evidence is required");
    expect(text).toContain("UNSUPPORTED");
    expect(text).not.toContain("Ownership retrieval failed");
    expect(text).not.toContain("no beneficial owners");
  },
);

it.each(["COMPLETE", "EMPTY", "UNSUPPORTED", "FAILED"] as const)(
  "retains distinct typed ownership status %s", (status) => {
    const source: RegistryAcquisition = { ...acquisition, operation_results: [
      acquisition.operation_results[0],
      { operation: "OWNERSHIP_PARTIES", status, record_count: status === "COMPLETE" ? 2 : 0, error: null, provenance: null },
    ] };
    const text = render(null, source).textContent ?? "";
    expect(text).toContain(status);
    expect(text.includes("Ownership retrieval failed")).toBe(status === "FAILED");
    expect(text.includes("Ownership unavailable from current registry evidence")).toBe(status === "EMPTY");
    expect(text.includes("2 ownership record(s) retrieved")).toBe(status === "COMPLETE");
    expect(text).not.toContain("not an authoritative partnership-ownership source");
  },
);

it("shows the retained configurable duration without imposing the old fixed 90-day label", () => {
  const view = render({ ...binding, freshness_duration_seconds: 60,
    freshness_policy_id: "MOCK_ACRA_APPROVED_POLICY", freshness_policy_version: 2,
    expires_at: "2026-09-20T00:01:01.123456Z" });
  expect(view.textContent).toContain("60 seconds");
  expect(view.textContent).toContain("MOCK_ACRA_APPROVED_POLICY version 2");
  expect(view.textContent).not.toContain("90 elapsed 24-hour periods");
});


it("renders Singapore rollover timestamps with separately inspectable original UTC", () => {
  const source = { ...acquisition, retrieved_at: "2026-10-13T16:00:00Z" };
  const view = render(binding, source);
  expect([...view.querySelectorAll(".kv-row")].find(row => row.querySelector(".kv-label")?.textContent === "Acquisition status")?.querySelector(".kv-value")?.textContent).toBe("COMPLETE");
  const row = Array.from(view.querySelectorAll(".kv-row")).find(item => item.textContent?.includes("Acquisition retrieved at"))!;
  expect(row.textContent).toContain("14 Oct 2026");
  expect(row.textContent).toContain("SGT");
  expect(row.textContent).not.toContain(source.retrieved_at);
  const detail = Array.from(view.querySelectorAll("details")).find(item => item.querySelector("summary")?.textContent?.includes("original ISO UTC"))!;
  expect(detail).toBeTruthy();
  expect(detail.textContent).toContain(source.retrieved_at);
  expect(detail.textContent).toContain(binding.bound_to_case_at);
  expect(detail.textContent).toContain(binding.expires_at);
});

it.each([null, undefined, "", "malformed", "2026-02-30T00:00:00Z"])("does not present missing/invalid registry time %s as usable", value => {
  const view = render({ ...binding, bound_to_case_at: value as string }, { ...acquisition, retrieved_at: value as string });
  const row = Array.from(view.querySelectorAll(".kv-row")).find(item => item.textContent?.includes("Acquisition retrieved at"))!;
  expect(row.textContent).toMatch(/Not recorded|Unavailable/);
  expect(view.textContent).not.toContain("Reused fresh registry evidence");
  expect(view.textContent).toContain("not a current validity assessment");
});

it("does not infer freshness from valid binding dates when retrieval provenance is invalid", () => {
  const view = render(binding, { ...acquisition, retrieved_at: "malformed" });
  expect(view.textContent).not.toContain("Reused fresh registry evidence");
  expect(view.textContent).toContain("valid-at-use timestamps unavailable");
});

it("exposes safe Main, business and audit subsets without nested technical controls", () => {
  container = document.createElement("div"); document.body.append(container); root = createRoot(container);
  const show = (part: "main" | "more" | "technical") => act(() => root?.render(
    <RegistryProvenancePanel acquisition={acquisition} binding={binding} part={part} />));
  show("main");
  expect(container.textContent).toContain("Identity retrieved");
  expect(container.textContent).toContain("Reused fresh registry evidence");
  expect(container.textContent).not.toContain("7776000 seconds");
  expect(container.querySelector("details")).toBeNull();
  show("more"); expect(container.textContent).toContain("SGT (UTC+08:00)");
  expect(container.textContent).not.toContain("EVALUATION_NOW_LT_EXPIRES_AT");
  show("technical");
  expect(container.textContent).toContain("7776000 seconds");
  expect(container.textContent).toContain("2026-09-20T00:00:01.123456Z");
  expect(container.textContent).toContain("EVALUATION_NOW_LT_EXPIRES_AT");
  expect(container.querySelector("details")).toBeNull();
});
