// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it } from "vitest";

import type { OwnershipAnalysisRecord, OwnershipPath } from "../types";
import OwnershipPathExplorer from "./OwnershipPathExplorer";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function path(index: number, edgeCount = 1): OwnershipPath {
  return {
    path_id: `path-${index}`,
    effective_ownership_percent: `0.${String(index).padStart(20, "0")}`,
    is_direct: edgeCount === 1,
    calculation: `exact(${index}) = 0.${String(index).padStart(20, "0")}`,
    edges: Array.from({ length: edgeCount }, (_, edge) => ({ relationship_id: `rel-${index}-${edge}`, parent_party_id: `entity-${edge}`, parent_display_name: `Owned Entity ${edge}`, child_party_id: `owner-${edge}`, child_display_name: `Owner ${edge}`, ownership_percent: `${edge}.000000000000000001` })),
  };
}

function record(paths = [path(1), path(2)], analysisId = "analysis-1"): OwnershipAnalysisRecord {
  return {
    case_id: "case", analysis_id: analysisId, correlation_id: "correlation", root_party_id: "root", provider_name: "DECIMAL_GRAPH_ENGINE", provider_environment: "LOCAL", state: "REVIEW_REQUIRED", parties: [], relationships: [],
    candidates: [{ party: { party_id: "candidate-1", display_name: "Candidate One", party_type: "NATURAL_PERSON", registration_number: null, country: "SG" }, direct_ownership_percent: "25.000000000000000001", indirect_ownership_percent: "12.340000000000000009", aggregated_ownership_percent: "37.340000000000000010", threshold_percent: "25.000000000000000000", threshold_comparator: "GREATER_THAN_OR_EQUAL_TO", threshold_result: "MET", classification: "REVIEW_REQUIRED", paths }],
    issues: [{ code: "CYCLE_DETECTED", message: "Exact retained cycle message.", affected_party_ids: ["candidate-1"] }], threshold_percent: "25.000000000000000000", threshold_comparator: "GREATER_THAN_OR_EQUAL_TO", events: [], error: null, created_at: "now", loaded_at: "now", analyzed_at: "now", updated_at: "now",
  };
}

let root: Root | null = null; let container: HTMLDivElement | null = null;
afterEach(() => { if (root) act(() => root?.unmount()); container?.remove(); root = null; container = null; });
function render(value: OwnershipAnalysisRecord | null) { container = document.createElement("div"); document.body.append(container); root = createRoot(container); act(() => root?.render(<OwnershipPathExplorer record={value} />)); return container; }
function click(label: string) { const button = [...container!.querySelectorAll("button")].find((item) => item.textContent === label)!; expect(button).toBeTruthy(); act(() => button.dispatchEvent(new MouseEvent("click", { bubbles: true }))); }

describe("OwnershipPathExplorer", () => {
  it("renders recovered owner identifiers, exact percentages and LOCAL source alongside UBO results", () => {
    const owner = { party_id: "candidate-1", display_name: "Candidate One", party_type: "NATURAL_PERSON" as const, registration_number: "safe-identifier", country: "SG" };
    const recovered: OwnershipAnalysisRecord = { ...record(), state: "ANALYZED", provider_name: "MANUAL_DECLARATION_POC", parties: [owner],
      relationships: [{ relationship_id: "manual-1", parent_party_id: "root", child_party_id: "candidate-1", ownership_percent: "60.000000000000000001", relationship_type: "OWNERSHIP", basis: "SHARE_OWNERSHIP", provenance: { provider: "MANUAL_DECLARATION_POC", environment: "LOCAL", sourced_at: "2026-10-01T00:00:00Z" } }], issues: [] };
    const view = render(recovered);
    const table = view.querySelector<HTMLTableElement>("table[aria-label='Retained ownership details']");
    expect(table).not.toBeNull();
    expect(table?.textContent).toContain("safe-identifier");
    expect(table?.textContent).toContain("60.000000000000000001%");
    expect(table?.textContent).toContain("LOCAL");
    expect(view.textContent).toContain("Client-supplied ownership evidence");
    expect(view.textContent).toContain("not ACRA-derived");
    expect(view.textContent).toContain("Threshold comparison");
  });

  it("preserves exact Decimal, calculation, comparator, result, classification and issue strings", () => {
    const view = render(record()); const text = view.textContent ?? "";
    expect(text).toContain("25.000000000000000001"); expect(text).toContain("12.340000000000000009"); expect(text).toContain("37.340000000000000010");
    expect(text).toContain("GREATER_THAN_OR_EQUAL_TO 25.000000000000000000 → MET"); expect(text).toContain("REVIEW_REQUIRED");
    expect(text).toContain("exact(1) = 0.00000000000000000001"); expect(text).toContain("CYCLE_DETECTED: Exact retained cycle message."); expect(text).toContain("Non-definitive partial ownership view");
  });

  it("uses keyboard-native pressed candidate and path buttons for multiple retained paths", () => {
    const view = render(record());
    const candidate = [...view.querySelectorAll("button")].find((item) => item.textContent === "Candidate One")!;
    expect(candidate.getAttribute("aria-pressed")).toBe("true");
    const second = [...view.querySelectorAll("button")].find((item) => item.textContent === "Inspect path-2")!;
    second.focus(); expect(document.activeElement).toBe(second); act(() => second.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }))); act(() => second.click());
    expect(second.getAttribute("aria-pressed")).toBe("true"); expect(view.textContent).toContain("Selected retained path: path-2");
  });

  it("bounds a long visual with prefix, suffix, and an explicit hidden-edge boundary", () => {
    const view = render(record([path(9, 15)])); const visual = view.querySelector('[aria-label="Selected ownership path visual"]')!;
    expect(visual.querySelectorAll("li")).toHaveLength(11);
    expect(visual.textContent).toContain("rel-9-0"); expect(visual.textContent).toContain("rel-9-14"); expect(visual.textContent).toContain("5 hidden edges between bounded prefix and suffix");
    expect(visual.textContent).toContain("is owned by");
  });

  it("paginates retained path rows twenty at a time", () => {
    const view = render(record(Array.from({ length: 21 }, (_, index) => path(index + 1))));
    expect(view.querySelectorAll("tbody tr")).toHaveLength(20); expect(view.textContent).toContain("page 1 of 2");
    click("Next paths"); expect(view.querySelectorAll("tbody tr")).toHaveLength(1); expect(view.textContent).toContain("page 2 of 2"); expect(view.textContent).toContain("path-21");
  });

  it("clamps page when same-analysis retained paths shrink", () => {
    const manyPaths = record(Array.from({ length: 21 }, (_, index) => path(index + 1)));
    const view = render(manyPaths);
    click("Next paths");
    expect(view.textContent).toContain("page 2 of 2");

    act(() => root?.render(<OwnershipPathExplorer record={record([path(1), path(2)])} />));

    expect(view.textContent).toContain("page 1 of 1");
    expect(view.querySelectorAll("tbody tr")).toHaveLength(2);
    expect(view.textContent).toContain("path-1");
    expect(view.textContent).toContain("path-2");
  });

  it("resets selection when analysis or retained paths change", () => {
    const first = record(); const view = render(first); click("Inspect path-2");
    act(() => root?.render(<OwnershipPathExplorer record={record([path(7)], "analysis-2")} />));
    expect(view.textContent).toContain("Selected retained path: path-7"); expect(view.textContent).not.toContain("Selected retained path: path-2");
  });

  it("handles unavailable analysis without controls or side effects", () => {
    const view = render(null); expect(view.textContent).toContain("Ownership analysis is not available"); expect(view.querySelector("button")).toBeNull();
  });
});
