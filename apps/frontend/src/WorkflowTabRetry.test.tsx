// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import { NewCaseStart } from "./pages/WorkflowTab";
import type { AuthenticatedProfile } from "./types";
import { createWorkflowCase, uploadWorkflowCaseDocument } from "./workflowApi";

vi.mock("./workflowApi", async (original) => ({
  ...(await original<typeof import("./workflowApi")>()),
  createWorkflowCase: vi.fn(),
  uploadWorkflowCaseDocument: vi.fn(),
}));

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const actor = { user_id: "maya-lim", role: "CLIENT_ONBOARDER", team_display_name: "Alpha" } as AuthenticatedProfile;
const workflow = { workflow_id: "workflow", name: "Refresh", case_source: "NEW_CASE" as const };
const run = { run_id: "run" };

describe("NewCaseStart retry", () => {
  let root: Root | null = null;
  afterEach(() => { act(() => root?.unmount()); root = null; document.body.innerHTML = ""; vi.clearAllMocks(); });

  function setValue(input: HTMLInputElement, value: string) {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  }

  it("keeps one case, fixes its details and skips uploaded files after a failed upload", async () => {
    vi.mocked(createWorkflowCase).mockResolvedValue({ run } as never);
    vi.mocked(uploadWorkflowCaseDocument)
      .mockResolvedValueOnce(run as never)
      .mockRejectedValueOnce(new Error("upload failed"))
      .mockResolvedValue(run as never);
    const onOpenRun = vi.fn();
    const host = document.createElement("div");
    document.body.append(host);
    root = createRoot(host);
    act(() => root!.render(
      <QueryClientProvider client={new QueryClient()}>
        <NewCaseStart actor={actor} workflow={workflow} onOpenRun={onOpenRun} />
      </QueryClientProvider>,
    ));
    const legalName = host.querySelector<HTMLInputElement>("#workflow-legal-name")!;
    act(() => {
      setValue(legalName, "Sample Limited");
      setValue(host.querySelector<HTMLInputElement>("#workflow-uen")!, "HK123");
    });
    const fileInput = host.querySelector<HTMLInputElement>('input[type="file"]')!;
    const first = new File(["a"], "first.txt", { type: "text/plain" });
    const second = new File(["b"], "second.txt", { type: "text/plain" });
    Object.defineProperty(fileInput, "files", { configurable: true, value: [first, second] });
    act(() => { fileInput.dispatchEvent(new Event("change", { bubbles: true })); });

    const submit = async () => {
      await act(async () => {
        host.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      });
    };
    await submit();
    await vi.waitFor(() => expect(host.textContent).toContain("company details are fixed"));
    expect(legalName.disabled).toBe(true);
    expect(onOpenRun).not.toHaveBeenCalled();

    await submit();
    await vi.waitFor(() => expect(onOpenRun).toHaveBeenCalledWith("run"));
    expect(createWorkflowCase).toHaveBeenCalledTimes(1);
    expect(vi.mocked(uploadWorkflowCaseDocument).mock.calls.map(call => (call[1] as File).name)).toEqual([
      "first.txt", "second.txt", "second.txt",
    ]);
  });
});
