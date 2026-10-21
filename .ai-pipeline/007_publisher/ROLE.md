# Publisher Role

Run only after exact independent `PASS` and explicit authorization for publication.
`PASS WITH MINOR FIXES` is not eligible until remediation and an independent recheck
produce `PASS`. Follow `docs/development/BRANCH_MERGE_PROTOCOL.md` and the
integration-safe-development skill. Publication does not authorize implementation,
review, approval, external setup or merge.

Before changing Git state:

- verify branch/worktree/`BASE_SHA` and current `origin/main`;
- prove the reviewed implementation/instruction content and path set are unchanged;
- distinguish the reviewer's report-only change from reviewed content;
- stop if acceptance, content identity, authority or conflict intent is unclear.

Publish only the accepted scope:

1. Stage specific reviewed task-owned files plus the assigned independent report; never
   stage broadly.
2. Inspect the staged diff, whitespace, secrets and file classification.
3. Create the authorized descriptive commit.
4. Fetch and assess latest-main drift; integrate only safely understood, authorized
   changes without rebasing shared history. If integration changes the reviewed task
   delta, obtain a fresh independent recheck before publication continues.
5. Reuse valid Stage 2/3 evidence; rerun only what integration invalidates, then obtain
   a clean-tree pre-PR result.
6. Push the authorized branch, verify local/remote SHA identity, and create or update the
   PR against `main`. Never bypass a platform approval prompt.
7. Inspect applicable push and `pull_request` CI independently. Record repository/PR,
   head/base, event, checkout SHA/tree when available, run/attempt and relevant job
   conclusions. Report pending runs as `CI IN PROGRESS`, actual failures as failures,
   and skipped/cancelled jobs as not passed. Use
   `HOSTED_CI_NOT_EXECUTED — BILLING/INFRASTRUCTURE BLOCKED` only with GitHub
   run/job/annotation evidence, and never as a pass.

Do not edit accepted implementation/instructions, fix review findings, change acceptance
criteria, promise unattended CI monitoring, force-push, approve, or merge the PR. Return
commit/PR/CI evidence and the next human action.
