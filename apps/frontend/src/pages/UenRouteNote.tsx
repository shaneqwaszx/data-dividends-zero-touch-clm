import type { UenRouteDecision } from "../types";

/** D-114: the backend's recorded route for the case's UEN, shown as written; never worked out here. */
export default function UenRouteNote({ route }: { route: UenRouteDecision | null | undefined }) {
  if (!route) return null;
  return <p className="control-help" data-testid="uen-route">Entity type from UEN: {route.description}</p>;
}
