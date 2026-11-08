// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it } from "vitest";

import type { OwnershipAnalysisRecord, OwnershipPath } from "../types";
import OwnershipPathExplorer, { OwnershipSupportingDetails } from "./OwnershipPathExplorer";
import StageDisclosure from "./StageDisclosure";

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
  it("renders recovered owner identifiers, rounded percentages and LOCAL source alongside UBO results", () => {
    const owner = { party_id: "candidate-1", display_name: "Candidate One", party_type: "NATURAL_PERSON" as const, registration_number: "safe-identifier", country: "SG" };
    const recovered: OwnershipAnalysisRecord = { ...record(), state: "ANALYZED", provider_name: "MANUAL_DECLARATION_POC", parties: [owner],
      relationships: [{ relationship_id: "manual-1", parent_party_id: "root", child_party_id: "candidate-1", ownership_percent: "60.000000000000000001", relationship_type: "OWNERSHIP", basis: "SHARE_OWNERSHIP", provenance: { provider: "MANUAL_DECLARATION_POC", environment: "LOCAL", sourced_at: "2026-10-01T00:00:00Z" } }], issues: [] };
    const view = render(recovered);
    const table = view.querySelector<HTMLTableElement>("table[aria-label='Retained ownership details']");
    expect(table).not.toBeNull();
    expect(table?.textContent).toContain("safe-identifier");
    expect(table?.textContent).toContain("60%");
    expect(table?.textContent).toContain("LOCAL");
    expect(view.textContent).toContain("Client-supplied ownership evidence");
    expect(view.textContent).toContain("not ACRA-derived");
    expect(view.textContent).toContain("Against the threshold");
  });

  it("rounds Decimal labels while preserving raw records, comparator, result, classification and issues", () => {
    const original = record(); const snapshot = structuredClone(original); const view = render(original); const text = view.textContent ?? "";
    expect(text).toContain("25%"); expect(text).toContain("12.34%"); expect(text).toContain("37.34%"); expect(original).toEqual(snapshot);
    expect(text).toContain("Meets the 25% threshold (25% or more)"); expect(text).toContain("Needs a person's review before any conclusion");
    // The backend MET result with a REVIEW_REQUIRED classification is never presented as a provisional UBO.
    expect(text).not.toContain("Provisional UBO candidate (meets the threshold; not verified)");
    expect(text).toContain("exact(1) = 0.00000000000000000001"); expect(text).toContain("CYCLE_DETECTED: Exact retained cycle message."); expect(text).toContain("Non-definitive partial ownership view");
  });

  it("uses keyboard-native pressed candidate and path buttons for multiple retained paths", () => {
    const retained = record(); retained.parties = retained.candidates.map(item => item.party); const view = render(retained);
    expect(view.querySelector('[aria-label="Ownership candidates"]')).toBeNull();
    const candidate = [...view.querySelectorAll("button")].find((item) => item.textContent === "Candidate One")!;
    expect(candidate.getAttribute("aria-pressed")).toBe("true");
    const second = [...view.querySelectorAll("button")].find((item) => item.textContent === "Inspect path-2")!;
    second.focus(); expect(document.activeElement).toBe(second); act(() => second.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }))); act(() => second.click());
    expect(second.getAttribute("aria-pressed")).toBe("true"); expect(view.textContent).toContain("Selected ownership route (2 of 2)"); expect(view.textContent).toContain("Route reference: path-2");
  });

  it("displays the actual tiny scientific API value without changing retained precision or classification", () => {
    // Two legal 0.000001% edges serialize their calculated effective interest as 1.00E-14.
    const original = record();
    const candidate = original.candidates[0];
    Object.assign(candidate, { direct_ownership_percent: "0", indirect_ownership_percent: "1.00E-14",
      aggregated_ownership_percent: "1.00E-14", threshold_percent: "25", threshold_result: "NOT_MET",
      classification: "BELOW_PROVISIONAL_THRESHOLD", paths: [{ path_id: "tiny-api-path", is_direct: false,
        effective_ownership_percent: "1.00E-14", calculation: "0.000001% x 0.000001% = 0.00000000000001%",
        edges: [{ relationship_id: "root-holding", parent_party_id: "root", parent_display_name: "Root",
          child_party_id: "holding", child_display_name: "Holding", ownership_percent: "0.000001" },
        { relationship_id: "holding-a", parent_party_id: "holding", parent_display_name: "Holding",
          child_party_id: "candidate-1", child_display_name: "Candidate One", ownership_percent: "0.000001" }] }] });
    original.threshold_percent = "25";
    const snapshot = structuredClone(original);
    const view = render(original);
    const detail = view.querySelector('[aria-label="Ownership candidate Candidate One"]')!;
    expect([...detail.querySelectorAll("dd")].slice(0, 3).map(item => item.textContent))
      .toEqual(["0%", "<0.01%", "<0.01%"]);
    expect(detail.textContent).toContain("Against the thresholdBelow the 25% threshold");
    expect(detail.textContent).toContain("ResultBelow the threshold");
    expect(detail.textContent).toContain("<0.01% × <0.01% = <0.01%");
    expect(detail.textContent).toContain("Effective ownership via this route: <0.01%");
    expect(original).toEqual(snapshot);
  });

  it("bounds a long visual with prefix, suffix, and an explicit hidden-edge boundary", () => {
    const view = render(record([path(9, 15)])); const visual = view.querySelector('[aria-label="Selected ownership path visual"]')!;
    expect(visual.querySelectorAll("li")).toHaveLength(11);
    expect(visual.textContent).toContain("rel-9-0"); expect(visual.textContent).toContain("rel-9-14"); expect(visual.textContent).toContain("5 hidden edges between bounded prefix and suffix");
    // Each edge reads owner first: the backend child holds a share of its parent.
    expect(visual.textContent).not.toContain("is owned by");
    expect(visual.querySelector("li")!.textContent).toMatch(/^Owner 0 owns .+ of /);
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
    expect(view.textContent).toContain("Route reference: path-7"); expect(view.textContent).not.toContain("Route reference: path-2");
  });

  it("handles unavailable analysis without controls or side effects", () => {
    const view = render(null); expect(view.textContent).toContain("Ownership analysis is not available"); expect(view.querySelector("button")).toBeNull();
  });

  it("does not enumerate hidden technical paths at the supported total/depth limits", () => {
    const retained = record();
    retained.candidates = Array.from({ length: 5 }, (_, candidateIndex) => ({
      ...retained.candidates[0],
      party: { ...retained.candidates[0].party, party_id: `candidate-${candidateIndex}` },
      paths: Array.from({ length: 1000 }, (_, index) => {
        const item = path(candidateIndex * 1000 + index + 1, 64);
        Object.defineProperty(item, "edges", { get() { throw new Error("Closed Technical details enumerated retained path edges"); } });
        return item;
      }),
    }));
    container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container);
    act(() => root?.render(<details><summary>Technical details</summary><OwnershipSupportingDetails record={retained} presentation="technical" /></details>));
    expect(container.querySelectorAll("*").length).toBeLessThan(100);
    expect(container.textContent).not.toContain("exact(5000)");
    expect(container.querySelector("details")?.open).toBe(false);
  });

  it("mounts exact technical paths only while native support is open and replaces analysis safely", () => {
    container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container);
    const show = (value: OwnershipAnalysisRecord) => act(() => root?.render(<details><summary>Technical details</summary><OwnershipSupportingDetails key={value.analysis_id} record={value} presentation="technical" /></details>));
    const first = record([path(1, 64), path(2, 64)]);
    show(first);
    expect(container.textContent).not.toContain("exact(2)");
    const details = container.querySelector("details")!;
    act(() => { details.open = true; details.dispatchEvent(new Event("toggle")); });
    expect(container.textContent).toContain(first.candidates[0].paths[1].calculation);
    expect(container.textContent).toContain("rel-2-63: 63.000000000000000001");
    expect(container.textContent).toContain(first.candidates[0].paths[1].effective_ownership_percent);
    show(record([path(7)], "new-analysis"));
    expect(container.textContent).toContain("exact(7)");
    expect(container.textContent).not.toContain("exact(2)");
    act(() => { details.open = false; details.dispatchEvent(new Event("toggle")); });
    expect(container.textContent).not.toContain("exact(7)");
    expect(container.querySelector("button, input, select, textarea")).toBeNull();
  });

  it("does not enumerate a replacement analysis while native scope reset closes Technical", () => {
    container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container);
    const hiddenReads: string[] = [];
    const tracked = (id: number) => {
      const value = record([path(id)], `analysis-${id}`);
      const item = value.candidates[0].paths[0]; const edges = item.edges;
      Object.defineProperty(item, "edges", { get() { if (!container?.querySelector("details")?.open) hiddenReads.push(item.path_id); return edges; } });
      return value;
    };
    const show = (scope: string, value: OwnershipAnalysisRecord) => act(() => root?.render(<StageDisclosure title="Ownership & UBO" scopeKey={scope} main={<p>Main</p>} technicalDetails={<OwnershipSupportingDetails key={value.analysis_id} record={value} presentation="technical" />} />));
    show("scope-a", tracked(1));
    const details = container.querySelector("details")!;
    act(() => { details.open = true; details.dispatchEvent(new Event("toggle")); });
    expect(container.textContent).toContain("exact(1)");
    show("scope-b", tracked(2));
    expect(details.open).toBe(false);
    expect(hiddenReads).toEqual([]);
    expect(container.textContent).not.toContain("exact(2)");
    act(() => { details.open = true; details.dispatchEvent(new Event("toggle")); });
    expect(container.textContent).toContain("exact(2)");
  });
});


describe("direct ownership primary inspection", () => {
  it.each([[60, 40], [50, 30, 20]])("keeps Selected holder primary without a redundant direct candidate/path table for %s", (...percentages) => {
    const value = record();
    value.issues = []; value.state = "ANALYZED";
    value.candidates = percentages.map((percent, index) => ({ ...value.candidates[0],
      party: { ...value.candidates[0].party, party_id: `person-${index}`, display_name: `Person ${index}` },
      direct_ownership_percent: String(percent), indirect_ownership_percent: "0", aggregated_ownership_percent: String(percent),
      paths: [{ ...path(index), effective_ownership_percent: String(percent), calculation: `${percent}% = ${percent}%`,
        edges: [{ relationship_id: `direct-${index}`, parent_party_id: "root", parent_display_name: "Synthetic root",
          child_party_id: `person-${index}`, child_display_name: `Person ${index}`, ownership_percent: String(percent) }] }],
    }));
    value.parties = [{ ...value.candidates[0].party, party_id: "root", display_name: "Synthetic root", party_type: "LEGAL_ENTITY" }, ...value.candidates.map(item => item.party)];
    value.relationships = value.candidates.map((item, index) => ({ relationship_id: `direct-${index}`, parent_party_id: "root",
      child_party_id: item.party.party_id, ownership_percent: item.direct_ownership_percent, relationship_type: "OWNERSHIP", basis: "SHARE_OWNERSHIP",
      provenance: { provider: "MOCK_REGISTRY", environment: "MOCK", sourced_at: "now" } }));
    container = document.createElement("div"); document.body.append(container); root = createRoot(container);
    act(() => root?.render(<OwnershipPathExplorer presentation="main" record={value} />));
    expect(container.querySelector('[aria-label^="Ownership candidate "]')).toBeNull();
    expect(container.querySelector('[aria-label^="Selected retained path "]')).toBeNull();
    expect([...container.querySelectorAll("caption")].some(item => item.textContent?.includes("Ownership routes for this person"))).toBe(false);
    const panel = container.querySelector('[aria-label="Selected holder"]')!;
    expect(panel.textContent).toContain("Person 0");
    click("Person 1"); expect(panel.textContent).toContain("Person 1");
    expect(panel.textContent).not.toContain("Person 0");
    expect(panel.textContent).toContain(`${percentages[1]}%`);
    expect(panel.textContent).toContain(`Calculation: ${percentages[1]}% = ${percentages[1]}%`);
    expect(panel.textContent).toContain("MOCK_REGISTRY · MOCK");
    expect(panel.textContent).toContain("Against the thresholdMeets the 25% threshold (25% or more)");
    expect(panel.textContent).not.toContain("GREATER_THAN_OR_EQUAL_TO");
  });
  it("keeps complex retained inspection optional and lazy with bounded pagination", () => {
    container = document.createElement("div"); document.body.append(container); root = createRoot(container);
    act(() => root?.render(<OwnershipPathExplorer presentation="main" record={record(Array.from({ length: 21 }, (_, i) => path(i + 1, 15)))} />));
    expect(container.querySelector('[aria-label^="Ownership candidate "]')).toBeNull();
    const support = [...container.querySelectorAll("details")].find(item => item.querySelector("summary")?.textContent === "Technical retained path inspection")!;
    expect(support).toBeTruthy();
    act(() => { support.open = true; support.dispatchEvent(new Event("toggle")); });
    expect(support.querySelectorAll("tbody tr")).toHaveLength(20);
    click("Next paths"); expect(support.querySelectorAll("tbody tr")).toHaveLength(1);
    expect(support.textContent).toContain("exact(21)");
    act(() => { support.open = false; support.dispatchEvent(new Event("toggle")); });
    expect(support.querySelector("tbody")).toBeNull();
  });
});


it("retains open multipath inspection when the same holder or another occurrence is reselected", () => {
  const value = record([path(1, 2), path(2, 2)]);
  const person = value.candidates[0].party;
  const party = (id: string) => ({ ...person, party_id: id, display_name: id, party_type: "LEGAL_ENTITY" as const });
  value.parties = [party("root"), party("holding-1"), party("holding-2"), person];
  value.candidates[0].paths = value.candidates[0].paths.map((item, index) => ({ ...item,
    edges: [{ ...item.edges[0], relationship_id: `root-holding-${index}`, parent_party_id: "root", parent_display_name: "root",
      child_party_id: `holding-${index + 1}`, child_display_name: `holding-${index + 1}` },
    { ...item.edges[1], relationship_id: `holding-person-${index}`, parent_party_id: `holding-${index + 1}`, parent_display_name: `holding-${index + 1}`,
      child_party_id: person.party_id, child_display_name: person.display_name }],
  }));
  value.relationships = value.candidates[0].paths.flatMap(item => item.edges.map(edge => ({ ...edge,
    relationship_type: "OWNERSHIP", basis: "SHARE_OWNERSHIP", provenance: { provider: "SYNTHETIC_RETAINED", environment: "LOCAL", sourced_at: "now" } })));
  container = document.createElement("div"); document.body.append(container); root = createRoot(container);
  act(() => root?.render(<OwnershipPathExplorer presentation="main" record={value} />));
  const support = [...container.querySelectorAll("details")].find(item => item.querySelector("summary")?.textContent === "Technical retained path inspection")!;
  act(() => { support.open = true; support.dispatchEvent(new Event("toggle")); });
  expect(support.querySelectorAll("tbody tr")).toHaveLength(2);
  const occurrences = [...container.querySelectorAll<HTMLButtonElement>('.ownership-structure__holder button')].filter(item => item.textContent === person.display_name);
  expect(occurrences).toHaveLength(2);
  for (const holder of occurrences) {
    act(() => holder.click());
    expect(support.open).toBe(true);
    expect(support.querySelectorAll("tbody tr")).toHaveLength(2);
    click("Inspect path-2");
    expect(support.querySelector('button[aria-pressed="true"]')?.textContent).toBe("Inspect path-2");
    expect(support.textContent).toContain("exact(2)");
  }
});

describe("RM-facing ownership wording", () => {
  const RAW_ENGINE_VALUES = ["GREATER_THAN_OR_EQUAL_TO", "PROVISIONAL_UBO_CANDIDATE", "BELOW_PROVISIONAL_THRESHOLD", "NOT_MET", "→ MET", "→ INDETERMINATE", "is owned by"];
  function everyClassification(): OwnershipAnalysisRecord {
    const value = record();
    value.issues = []; value.state = "ANALYZED";
    const results = [["PROVISIONAL_UBO_CANDIDATE", "MET", "30"], ["BELOW_PROVISIONAL_THRESHOLD", "NOT_MET", "24.999999999999999999"],
      ["REVIEW_REQUIRED", "INDETERMINATE", "40"], ["INDETERMINATE", "INDETERMINATE", "10"]] as const;
    value.candidates = results.map(([classification, threshold_result, percent], index) => ({ ...value.candidates[0],
      party: { ...value.candidates[0].party, party_id: `person-${index}`, display_name: `Person ${index}` },
      direct_ownership_percent: percent, indirect_ownership_percent: "0", aggregated_ownership_percent: percent,
      classification, threshold_result, paths: [path(index + 1)] }));
    value.parties = [{ ...value.candidates[0].party, party_id: "root", display_name: "Client root", party_type: "LEGAL_ENTITY" }, ...value.candidates.map(item => item.party)];
    value.relationships = value.candidates.map((item, index) => ({ relationship_id: `rel-${index + 1}-0`, parent_party_id: "root",
      child_party_id: item.party.party_id, ownership_percent: item.direct_ownership_percent, relationship_type: "OWNERSHIP", basis: "SHARE_OWNERSHIP",
      provenance: { provider: "MOCK_REGISTRY", environment: "MOCK", sourced_at: "now" } }));
    return value;
  }

  it("shows no raw engine value in the RM's main ownership view, for every person selected", () => {
    container = document.createElement("div"); document.body.append(container); root = createRoot(container);
    act(() => root?.render(<OwnershipPathExplorer presentation="main" record={everyClassification()} />));
    for (const name of ["Person 0", "Person 1", "Person 2", "Person 3"]) {
      click(name);
      for (const raw of RAW_ENGINE_VALUES) expect(container.textContent).not.toContain(raw);
    }
    const panel = container.querySelector('[aria-label="Selected holder"]')!;
    click("Person 1");
    // 24.999...% displays as 25% but stays below the inclusive threshold, as the backend decided.
    expect(panel.textContent).toContain("Against the thresholdBelow the 25% threshold");
    expect(panel.textContent).toContain("ResultBelow the threshold");
    click("Person 0");
    expect(panel.textContent).toContain("Against the thresholdMeets the 25% threshold (25% or more)");
    expect(panel.textContent).toContain("Client root · client");
    expect(panel.textContent).toContain("Person 0 owns 30% of Client root");
    // The legal disclaimers stay visible.
    expect(container.textContent).toContain("provisional, not a legal determination");
    expect(container.textContent).toContain("not a legal UBO determination");
  });

  it("keeps the exact backend values in the technical view", () => {
    container = document.createElement("div"); document.body.append(container); root = createRoot(container);
    act(() => root?.render(<OwnershipSupportingDetails record={everyClassification()} presentation="technical" />));
    const text = container.textContent ?? "";
    expect(text).toContain("Exact retained threshold: GREATER_THAN_OR_EQUAL_TO 25.000000000000000000");
    expect(text).toContain("Person 0 · PROVISIONAL_UBO_CANDIDATE");
    expect(text).toContain("Person 1 · BELOW_PROVISIONAL_THRESHOLD");
    expect(text).toContain("GREATER_THAN_OR_EQUAL_TO 25.000000000000000000 · NOT_MET");
    expect(text).toContain("24.999999999999999999");
  });
});
