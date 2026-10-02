// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { describe, expect, it } from "vitest";
import StageDisclosure, { revealStage } from "./StageDisclosure";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

describe("stage disclosure", () => {
  it("uses keyboard-operable buttons with labelled controlled content and follows the current stage", async () => {
    const host = document.createElement("div");
    document.body.append(host);
    const root = createRoot(host);
    const render = (active: boolean) => root.render(<StageDisclosure title="Ownership & UBO" active={active}><p id="evidence">Evidence</p></StageDisclosure>);
    await act(async () => render(false));
    const button = host.querySelector("button")!;
    expect(button.type).toBe("button");
    expect(button.getAttribute("aria-expanded")).toBe("false");
    expect(document.getElementById(button.getAttribute("aria-controls")!)?.hidden).toBe(true);
    await act(async () => button.click());
    expect(button.getAttribute("aria-expanded")).toBe("true");
    await act(async () => render(true));
    expect(button.getAttribute("aria-expanded")).toBe("true");
    await act(async () => render(false));
    expect(button.getAttribute("aria-expanded")).toBe("false");
    await act(async () => revealStage(host.querySelector("#evidence")!));
    expect(button.getAttribute("aria-expanded")).toBe("true");
    await act(async () => root.unmount());
    host.remove();
  });
});
