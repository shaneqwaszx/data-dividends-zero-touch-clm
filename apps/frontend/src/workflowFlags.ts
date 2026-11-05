/** On unless explicitly set to "false"; unit tests set that so they see no extra request. */
export function workflowManagerEnabled(): boolean {
  return import.meta.env.VITE_WORKFLOW_MANAGER_ENABLED !== "false";
}
