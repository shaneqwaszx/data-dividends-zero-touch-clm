// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from "vitest";

import { findCaseSection, goToCaseSection } from "./caseSections";

function stage(title: string): HTMLElement {
  const section = document.createElement("section");
  section.className = "stage-disclosure";
  section.innerHTML = `<h2><button type="button"><span>${title}</span><span>+</span></button></h2>`;
  document.body.appendChild(section);
  return section;
}

afterEach(() => {
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("goToCaseSection", () => {
  it("opens and scrolls to the named stage, and moves focus to its heading", () => {
    stage("Registry verification");
    const target = stage("Document verification");
    const scroll = vi.fn();
    target.scrollIntoView = scroll;
    const revealed = vi.fn();
    target.addEventListener("reveal-stage", revealed);

    expect(goToCaseSection("Document verification")).toBe(true);
    expect(revealed).toHaveBeenCalledTimes(1);
    expect(scroll).toHaveBeenCalledWith(expect.objectContaining({ block: "start" }));
    expect(document.activeElement).toBe(target.querySelector("h2 > button"));
  });

  it("does nothing when the stage is not on the page", () => {
    stage("Registry verification");
    expect(findCaseSection("Ownership & UBO")).toBeNull();
    expect(goToCaseSection("Ownership & UBO")).toBe(false);
  });
});
