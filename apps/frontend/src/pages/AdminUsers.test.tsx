// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { AdminProfile } from "../types";

const api = vi.hoisted(() => ({
  fetchAdminProfiles: vi.fn(),
  fetchTeamOptions: vi.fn(),
  createAdminProfile: vi.fn(),
  updateAdminProfile: vi.fn(),
  resetAdminProfilePassword: vi.fn(),
  disableAdminProfileSignIn: vi.fn(),
}));

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  return { ApiError: actual.ApiError, ...api };
});

import { ApiError } from "../api";
import AdminUsers from "./AdminUsers";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function profile(user_id: string, role: AdminProfile["role"], version = 1): AdminProfile {
  return {
    user_id, display_name: `Synthetic ${user_id}`, role,
    team_id: role === "RELATIONSHIP_MANAGER" ? "TEAM_A" : null,
    team_display_name: role === "RELATIONSHIP_MANAGER" ? "Alpha" : null,
    version, created_at: "2026-11-16T00:00:00Z", updated_at: "2026-11-16T00:00:00Z",
    created_by: "system-bootstrap", updated_by: "system-bootstrap",
  };
}

const rm = profile("synthetic-rm", "RELATIONSHIP_MANAGER", 3);
const hr = profile("synthetic-hr", "HR");
const newPassword = "synthetic-reset-value-1";

let root: Root;
let container: HTMLDivElement;

async function render() {
  await act(async () => { root.render(<AdminUsers />); });
}

function button(name: string): HTMLButtonElement | undefined {
  return [...container.querySelectorAll("button")].find(
    (item) => (item.getAttribute("aria-label") ?? item.textContent) === name,
  );
}

function resetInputs(): HTMLInputElement[] {
  const form = container.querySelector<HTMLFormElement>(`form[aria-label^="Reset password for"]`);
  return form ? [...form.querySelectorAll<HTMLInputElement>('input[type="password"]')] : [];
}

function type(input: HTMLInputElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
  setter?.call(input, value);
  input.dispatchEvent(new Event("input", { bubbles: true }));
}

async function openAndSubmit(user: string, value: string, confirmation: string) {
  await act(async () => { button(`Reset password for ${user}`)?.click(); });
  const [first, second] = resetInputs();
  await act(async () => { type(first, value); type(second, confirmation); });
  const form = container.querySelector<HTMLFormElement>(`form[aria-label="Reset password for ${user}"]`);
  await act(async () => { form?.requestSubmit(); });
}

describe("D-140 HR password reset", () => {
  beforeEach(() => {
    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
    api.fetchAdminProfiles.mockResolvedValue([rm, hr]);
    api.fetchTeamOptions.mockResolvedValue([]);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  it("offers reset only for non-HR users and hides the form until asked", async () => {
    await render();
    expect(button("Reset password for synthetic-rm")).toBeDefined();
    expect(button("Reset password for synthetic-hr")).toBeUndefined();
    expect(button("Disable sign-in for synthetic-rm")).toBeDefined();
    expect(button("Disable sign-in for synthetic-hr")).toBeUndefined();
    expect(resetInputs()).toHaveLength(0);
  });

  it("sends the version and password once, updates the row and clears both fields", async () => {
    api.resetAdminProfilePassword.mockResolvedValue({ ...rm, version: 4, updated_by: "synthetic-hr" });
    await render();

    await openAndSubmit("synthetic-rm", newPassword, newPassword);

    expect(api.resetAdminProfilePassword).toHaveBeenCalledTimes(1);
    expect(api.resetAdminProfilePassword).toHaveBeenCalledWith("synthetic-rm", { expected_version: 3, new_password: newPassword });
    expect(resetInputs()).toHaveLength(0);
    expect(container.textContent).toContain("Password reset for synthetic-rm");
    expect(container.querySelector("tbody")?.textContent).toContain("4");
    expect(container.innerHTML).not.toContain(newPassword);
  });

  it("refuses a mismatched confirmation locally and clears both fields", async () => {
    await render();

    await openAndSubmit("synthetic-rm", newPassword, `${newPassword}-different`);

    expect(api.resetAdminProfilePassword).not.toHaveBeenCalled();
    expect(container.textContent).toContain("Password confirmation does not match.");
    expect(resetInputs().map((input) => input.value)).toEqual(["", ""]);
  });

  it("clears both fields on a backend failure and refreshes versions on conflict", async () => {
    api.resetAdminProfilePassword.mockRejectedValue(
      new ApiError("The administration record changed or conflicts with an existing record.", 409, "ADMINISTRATION_CONFLICT"),
    );
    api.fetchAdminProfiles.mockResolvedValueOnce([rm, hr]).mockResolvedValueOnce([{ ...rm, version: 5 }, hr]);
    await render();

    await openAndSubmit("synthetic-rm", newPassword, newPassword);

    expect(container.textContent).toContain("The administration record changed");
    expect(api.fetchAdminProfiles).toHaveBeenCalledTimes(2);
    expect(resetInputs().map((input) => input.value)).toEqual(["", ""]);
    expect(container.innerHTML).not.toContain(newPassword);
  });

  it("requires confirmation, then shows disabled status and restores sign-in through reset", async () => {
    const confirm = vi.spyOn(globalThis, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
    api.disableAdminProfileSignIn.mockResolvedValue({ ...rm, version: 4, sign_in_disabled: true });
    api.resetAdminProfilePassword.mockResolvedValue({ ...rm, version: 5, sign_in_disabled: false });
    await render();

    await act(async () => { button("Disable sign-in for synthetic-rm")?.click(); });
    expect(api.disableAdminProfileSignIn).not.toHaveBeenCalled();
    await act(async () => { button("Disable sign-in for synthetic-rm")?.click(); });
    expect(confirm).toHaveBeenCalledTimes(2);
    expect(api.disableAdminProfileSignIn).toHaveBeenCalledExactlyOnceWith("synthetic-rm", 3);
    expect(container.querySelector("tbody")?.textContent).toContain("Sign-in disabled");
    expect(button("Disable sign-in for synthetic-rm")).toBeUndefined();

    await openAndSubmit("synthetic-rm", newPassword, newPassword);
    expect(api.resetAdminProfilePassword).toHaveBeenCalledExactlyOnceWith(
      "synthetic-rm", { expected_version: 4, new_password: newPassword },
    );
    expect(button("Disable sign-in for synthetic-rm")).toBeDefined();
    expect(container.querySelector("tbody")?.textContent).not.toContain("Sign-in disabled");
  });

  it("refreshes a stale disable without retrying or claiming success", async () => {
    vi.spyOn(globalThis, "confirm").mockReturnValue(true);
    api.disableAdminProfileSignIn.mockRejectedValue(new ApiError("Record changed.", 409, "ADMINISTRATION_CONFLICT"));
    api.fetchAdminProfiles.mockResolvedValueOnce([rm, hr]).mockResolvedValueOnce([{ ...rm, version: 5 }, hr]);
    await render();

    await act(async () => { button("Disable sign-in for synthetic-rm")?.click(); });
    expect(api.disableAdminProfileSignIn).toHaveBeenCalledExactlyOnceWith("synthetic-rm", 3);
    expect(api.fetchAdminProfiles).toHaveBeenCalledTimes(2);
    expect(container.textContent).toContain("Record changed.");
    expect(container.querySelector("tbody")?.textContent).toContain("5");
    expect(container.querySelector("tbody")?.textContent).not.toContain("Sign-in disabled");
  });
});
