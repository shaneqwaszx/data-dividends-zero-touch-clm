# Pre-Phase 22 Manual-UAT Stabilization — Reflection

Implementation and investigation reflection:

- The shared nav pressure point, two-column breakpoint, local scroll owners, and account hover are repaired at their design-system owner rather than per-screen offsets or global clipping.
- Removing the final unsupported dialog consumers reduced code and aligned operational controls with Q-016; no replacement workflow was invented.
- Mongo evidence disproved deletion and separated runtime composition from stored data.
- Git history proved the exact Garden file lifecycle and stopped restoration at the provider-authority boundary.
- Verification uncovered a Windows-only checker defect. The bounded fix improves the existing read-only verifier and has dedicated tests; it does not expand product scope.
- The first independent gate found a real evidence defect: the responsive test simulated ordinary navigation with repeated full reloads, eventually stalling fresh focused runs. Replacing only those transitions with actual workspace links made the same acceptance matrix pass four fresh repetitions and better matches manual UAT. Programmatic focus was also replaced with a real Tab transition, and the retained-intake child route is asserted as a valid canonical destination.
- Same-pattern review found redundant full reloads inside the supported document-review test. Retaining its initial deep link and final reload while exercising intermediate decisions live makes the test stronger and repeatable in fresh lifecycles.
- The second gate correctly rejected isolated substitutes for the configured CI command. The recurrence generator was the runner's shared process-local backend lifecycle combined with ordinary full reloads inside tests. Dynamic per-test lifecycle isolation plus removal of the remaining ordinary reload sites closes both paths without retrying or weakening coverage; the exact unfiltered command now passes twice consecutively.

Reflection remains open until fresh independent re-QG, local commit, clean-tree pre-PR, and running-demo verification complete. Method Pack output does not grant completion authority.
