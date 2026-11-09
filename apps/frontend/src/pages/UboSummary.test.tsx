// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it } from "vitest";
import type { OwnershipAnalysisRecord } from "../types";
import { fiveLayerAssumedBasisFixture, gardenAssumedBasisFixture } from "./ownershipAssumedBasisFixture";
import OwnershipPathExplorer from "./OwnershipPathExplorer";
import { ownershipStructureFixture } from "./ownershipStructureFixture";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const HEADING = "Meets the threshold on an assumed basis — review required";
const EXPLANATION = "These percentages meet the configured threshold under declared POC assumptions. They are not verified or provisionally classified UBOs and do not clear ownership readiness.";
let root: Root; let host: HTMLDivElement;
afterEach(() => { act(() => root.unmount()); host.remove(); });
function render(record: OwnershipAnalysisRecord) {
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  act(() => root.render(<OwnershipPathExplorer record={record} />));
  return host;
}
function stat(label: string) {
  return [...host.querySelectorAll(".ownership-analysis__stats > div")].find(item => item.querySelector("dt")?.textContent === label)?.querySelector("dd")?.textContent ?? null;
}
function assumedSection() { return host.querySelector<HTMLElement>(`section[aria-label="${HEADING}"]`); }
function assumedCards() {
  return [...(assumedSection()?.querySelectorAll<HTMLElement>(".ubo-card") ?? [])].map(card => ({
    name: card.querySelector(".ubo-card__name")!.textContent,
    effective: card.querySelector(".ubo-card__effective b")!.textContent,
    text: card.textContent ?? "",
  }));
}
function selectHolder(name: string) {
  const target = [...host.querySelectorAll<HTMLButtonElement>(".ownership-node__body > button")].find(item => item.textContent === name)!;
  act(() => target.click());
  return host.querySelector<HTMLElement>('[aria-label="Selected holder"]')!;
}

describe("D-081 assumed-basis threshold matches stay apart from formal UBO classification", () => {
  it("Garden: four assessed people, two assumed-basis matches and zero formal provisional UBOs", () => {
    render(gardenAssumedBasisFixture());
    expect(stat("People assessed")).toBe("4");
    expect(stat("Provisional UBOs")).toBe("0");
    expect(stat("Assumed-basis matches")).toBe("2");
    expect(host.querySelector('[aria-label="Hierarchy summary"]')!.textContent).toContain("0 provisional UBOs");
    expect(host.querySelectorAll(".ownership-structure__row.is-ubo")).toHaveLength(0);
    expect(host.querySelector(".ubo-summary__empty")!.textContent).toBe(
      "No natural person is formally classified as a provisional UBO; 2 meet the threshold only on an assumed basis (below).",
    );
    expect(host.querySelector(".ubo-summary__list:not(.ubo-summary__assumed *)")).toBeNull();
    expect(host.textContent).toContain("UBO determination requires review");
  });

  it("lists ABCD123 and LIM CHOON HUAT with their basis, and never TAN WEI LING or EFGH2345", () => {
    render(gardenAssumedBasisFixture());
    const section = assumedSection()!;
    expect(section.querySelector("h6")!.textContent).toBe(HEADING);
    expect(section.textContent).toContain(EXPLANATION);
    const cards = assumedCards();
    expect(cards.map(card => [card.name, card.effective])).toEqual([["ABCD123", "51.14%"], ["LIM CHOON HUAT", "37.5%"]]);
    expect(cards[0].text).toContain("POC equal-unit assumption");
    expect(cards[1].text).toContain("Local synthetic overlay basis");
    for (const card of cards) {
      expect(card.text).toContain("On the assumed POC basisMeets the 25% threshold (25% or more) (not a classification)");
      expect(card.text).toContain("StatusNeeds a person's review before any conclusion");
      // An assumed-basis match is never presented as a formal provisional UBO.
      expect(card.text).not.toContain("Provisional UBO candidate");
      expect(card.text).not.toContain("PROVISIONAL_UBO_CANDIDATE");
    }
    expect(section.textContent).not.toContain("TAN WEI LING");
    expect(section.textContent).not.toContain("EFGH2345");
  });

  it("shows the assumed-basis comparison in the selected holder apart from the formal result", () => {
    render(gardenAssumedBasisFixture());
    const abcd = selectHolder("ABCD123");
    expect(abcd.textContent).toContain("Against the thresholdCannot be determined from the available records");
    expect(abcd.textContent).toContain("On the assumed POC basisMeets the 25% threshold (25% or more) (not a classification)");
    expect(abcd.textContent).toContain("ResultNeeds a person's review before any conclusion");
    const tan = selectHolder("TAN WEI LING");
    expect(tan.textContent).toContain("On the assumed POC basisBelow the 25% threshold (not a classification)");
    expect(tan.textContent).toContain("ResultNeeds a person's review before any conclusion");
  });

  it("keeps the existing provisional UBO fixture exactly as before", () => {
    render(ownershipStructureFixture());
    expect(stat("Provisional UBOs")).toBe("1");
    expect(stat("Assumed-basis matches")).toBeNull();
    expect(assumedSection()).toBeNull();
    expect(host.querySelector(".ubo-summary .ubo-card__name")!.textContent).toBe("Synthetic qualifying person");
    expect(host.querySelector(".ubo-summary__empty")).toBeNull();
    expect(selectHolder("Synthetic qualifying person").textContent).not.toContain("On the assumed POC basis");
  });

  it("keeps the previous behaviour when the optional field is absent", () => {
    const record = gardenAssumedBasisFixture();
    for (const candidate of record.candidates) delete candidate.synthetic_basis_threshold_result;
    render(record);
    expect(stat("Provisional UBOs")).toBe("0");
    expect(stat("Assumed-basis matches")).toBeNull();
    expect(assumedSection()).toBeNull();
    expect(host.querySelector(".ubo-summary__empty")!.textContent).toBe(
      "No qualifying natural person is identified by the current retained classification.",
    );
    expect(selectHolder("ABCD123").textContent).not.toContain("On the assumed POC basis");
  });

  it("five-layer overlay: BEATRICE LIM and DIANA KOH match on the local synthetic basis", () => {
    render(fiveLayerAssumedBasisFixture());
    expect(stat("Provisional UBOs")).toBe("0");
    expect(stat("Assumed-basis matches")).toBe("2");
    const cards = assumedCards();
    expect(cards.map(card => [card.name, card.effective])).toEqual([
      ["BEATRICE LIM (SYNTHETIC PERSON)", "37.5%"], ["DIANA KOH (SYNTHETIC PERSON)", "25%"],
    ]);
    expect(cards.every(card => card.text.includes("Local synthetic overlay basis"))).toBe(true);
    expect(assumedSection()!.textContent).not.toContain("ALEX TAN");
  });

});
