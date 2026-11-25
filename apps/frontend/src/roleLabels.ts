import type { Role } from "./types";

/**
 * Display text for a role. Presentation only: the role value itself (for example "HR")
 * is what the backend sends and checks, and it is unchanged.
 */
export function roleLabel(role: Role): string {
  if (role === "HR") return "Biz Ops";
  return role.replaceAll("_", " ");
}
