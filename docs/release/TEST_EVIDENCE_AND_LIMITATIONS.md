# Test evidence and limitations

| Field | Value |
|---|---|
| Evidence date | 2026-11-14, Windows 11, Python 3.12.10, Docker Desktop 29.9.3 (Compose 5.7.0), Git Bash |
| Evidence class | **Mock and Local only.** No command reached the Lightsail host, AWS, GHCR or an AI provider. Nothing here is Sandbox or Live evidence |
| Base | `origin/main` `d0142d8e8d74ea8002a72ec63bad8bbaf0f59410` |
| Tested content | See the handoff in `outputs/release-pipeline-20261114/` for the exact commits and trees: the tree the independent reviewer read, and the final tree after its findings were addressed, are different and are named separately there |

## 1. Automated tests (`tests/release`)

`python -m pytest tests/release -q -p no:cacheprovider` on the final tree: **321 passed, 1 skipped** (6 test files, 212 test functions; the count includes parametrised cases).
The one skipped test is the opt-in Windows Credential Manager round trip
(`CLM_RELEASE_WINCRED_SELFTEST=1`); it was run once by hand and passed (it writes and removes
one throwaway entry holding a sentinel value).

| Requirement | Tests (file `tests/release/...`) |
|---|---|
| Wrong commit, wrong tree, abbreviated commit, dirty or untracked state, commit not on the baseline | `test_source_images_render.py`: `test_wrong_commit_tree_or_abbreviated_commit_is_refused`, `test_dirty_or_untracked_state_...`, `test_commit_that_is_not_on_the_integration_baseline_is_refused` (real throwaway Git repository) |
| Wrong image id, wrong platform, never rebuilt | `test_existing_candidate_is_accepted_only_by_its_exact_image_id`, `test_a_local_image_that_changed_since_qualification_is_never_published` |
| Wrong digest (registry, host, archive) | `test_registry_content_that_is_not_the_qualified_image_is_refused`, `test_wrong_digest_on_the_host_is_refused`, `test_archive_damaged_in_transit_...`, `test_archive_of_a_different_image_...` |
| Missing and expired approval; other manifest, services, action, risk; window cap; reuse; expiry during the run | `test_core_and_manifest.py` approval tests; `test_deploy.py`: `test_execute_without_an_approval_...`, `test_expired_approval_...`, `test_approval_for_other_services_...`, `test_window_too_short_...`, `test_expiry_during_the_run_stops_before_the_next_change_and_does_not_roll_back`, `test_an_approval_cannot_be_used_twice` |
| Secret exposure | `test_secret_cannot_be_printed_formatted_or_pickled`, `test_redaction_...`, `test_gate_refuses_secret_in_argument_or_environment`, `test_audit_log_never_holds_a_secret`, `test_pull_token_travels_only_on_stdin_and_reaches_no_log_or_record`, `test_publish_pushes_..._without_exposing_the_token`, failure paths in `test_registry_content_...` and `test_failed_image_pull_...`, credential-store tests |
| Unsupported overlay combinations | `test_unsupported_overlay_combinations_are_refused` (8 cases), `test_wrappers_follow_the_runbook_and_refuse_absent_overlays`, `test_manifest_overlay_order_must_be_the_supported_one` |
| Unauthorised service change | `test_a_service_outside_the_approval_that_would_be_recreated_stops_the_run`, `test_backend_hash_change_without_approval_is_named_as_unauthorised`, `test_services_the_applier_never_changes_are_refused`, `test_host_render_with_an_undeclared_network_is_refused` |
| Failed preflight | `test_failed_preflight_stops_with_nothing_changed` (8 cases), `test_unhealthy_container_and_missing_rollback_image_fail_preflight`, `test_stateful_release_needs_a_recent_backup_...`, `test_backend_release_needs_the_running_backend_confirmed_on_the_host` |
| Failed image pull | `test_failed_image_pull_changes_nothing_and_leaves_the_approval_usable` |
| Duplicate or overlapping deployment | `test_overlapping_deployment_is_refused_by_the_local_lock`, `test_stale_local_lock_is_never_stolen_silently`, host lock in the preflight cases, `test_controller_refuses_to_run_beside_another_release_operation` |
| Health-check failure | `test_frontend_health_failure_rolls_back_automatically` (2 cases), `test_smoke_failure_rolls_the_frontend_back` |
| Rollback eligibility and refusal, including schema 19 | `test_schema_19_backend_is_never_an_eligible_rollback_target`, `test_automatic_rollback_needs_proof`, `test_assistant_failure_is_held_...`, `test_stateful_backend_is_never_rolled_back_blindly`, `test_backend_with_proven_compatibility_and_owner_consent_rolls_back`, `test_rollback_is_not_run_when_the_owner_did_not_approve_it`, `test_owner_requested_rollback_follows_the_same_eligibility_rules` |
| Mongo volume preservation and forbidden Compose verbs | `test_forbidden_host_commands_are_refused_before_they_run` (18 cases), `test_mongo_volume_identity_change_stops_the_run_and_volumes_are_never_removed`, `test_mongo_is_never_stopped_started_or_recreated_by_any_run`, `test_mongo_volume_must_stay_external_and_mongo_stays_private`, forbidden-word assertions on every command of the happy paths |
| Protected GoldTier and assistant networking in the rendered configuration | `test_assistant_networking_is_protected_even_when_declared`, `test_goldtier_and_backend_networking_is_protected_even_when_declared`, `test_real_render_keeps_goldtier_and_assistant_boundaries` (real offline `docker compose config`), `test_render_refuses_a_compose_file_that_adds_a_network` (real render of a modified copy) |
| Dry-run and plan-only issue no host write, no registry write, no provider call | `test_non_executing_modes_never_issue_a_host_or_registry_write`, `test_provider_call_is_refused_in_every_mode`, `test_dry_run_issues_no_host_write_no_registry_write_and_no_provider_call` (3 cases), `test_offline_dry_run_contacts_nothing_at_all`, `test_plan_only_and_validation_sets_never_reach_the_host`, `test_publish_dry_run_issues_no_registry_write_and_reads_no_credential`, `test_cli_offline_dry_run_of_the_sample_contacts_nothing` |
| Controller never promotes | `test_controller_prepares_a_promotion_ready_record_and_stops_there`, `test_controller_mode_cannot_publish_or_deploy_even_if_asked`, `test_failed_request_is_recorded_and_retried_only_on_request` |
| Owner-only actions | `test_only_the_owner_at_a_terminal_can_create_an_approval`, `test_cli_owner_only_commands_refuse_a_non_interactive_caller`, `test_owner_acceptance_moves_known_good_...` |

## 2. Other checks run on the final tree

| Check | Result |
|---|---|
| `ruff check --select E,F,I,UP,B,SIM --line-length 100 --target-version py312 tools/release tests/release` | All checks passed. **Only with these options.** No ruff configuration is tracked at the repository root, so a bare `ruff check tools/release tests/release` uses ruff's defaults or a parent configuration and is not clean (the re-reviewer saw 21 findings from rules outside this set) |
| `ruff format --check` (same options) | 24 files already formatted |
| `mypy --strict -p tools.release` | Success: no issues found in 19 source files |
| `python scripts/check_secrets.py` (worktree root) | Secret scan passed |
| `python -m pytest tests/deploy -q -p no:cacheprovider` from Git Bash | 116 passed, 1 skipped |
| `scripts/check_project_state.py`, `check_architecture.py`, `check_tooling_config.py`, `check_policy_authority.py`, `check_external_provider_readiness.py` | all five PASS |
| `python scripts/pre_pr_check.py` on the clean committed state | PASS (0 unsafe conditions, 0 warnings) on commit `e6356a1`, with the untracked `outputs/` handoff folder moved aside for the run |
| `release.ps1 checks --change-class CI_TOOLING` (the toolchain running its own selection) | On commit `e6356a1`: 12 checks PASS (5 governance scripts, `check_secrets`, `deploy-pytest`, `pre-pr-check`, `release-ruff`, `release-mypy`, `release-pytest`, `security-unittests`); the 4 manual CI jobs listed `NOT_RUN` |

Not run, and not claimed: the backend, assistant and frontend suites, the E2E shards, the
physical Mongo job, the local OCR job and the Windows demo-lifecycle job. This change touches
none of that code; `release.ps1 checks` lists those CI jobs as `NOT_RUN`.

## 3. Local evidence on the real `d0142d8` candidates (Local, not Live)

`release.ps1 image` was run against the three existing local images, accepting each by its
recorded id (no build). It reproduced the hand-recorded evidence in
`outputs/release-images-d0142d8-20261114/` in the main checkout:

| Image | Local id (= config digest; classic image store) | In-image files equal to the commit | Other |
|---|---|---|---|
| `clm-rc-frontend:d0142d8` | `sha256:5d566ea5...57f129` | 1 of 1 (`/etc/caddy/Caddyfile`) | |
| `clm-rc-backend:d0142d8` | `sha256:7d36daa3...3c792c` | 142 of 142 (`app`) | case-snapshot schema 20, read from the commit |
| `clm-rc-assistant:d0142d8` | `sha256:e98a00b2...7bbd12` | 99 of 99 (`ai_assistant`, `assistant_hosting`, `assistant_eval`, hosted profiles, lock file, two scripts) | fingerprint `d6955c9d2f97e3cba8b96409a5d4e3951691a156b822baef1acabb5974c6d281`, computed in the image with networking disabled; equal to the value reviewed for PR #180 |

The assistant count of 99 equals the coordinator's hand count.
`docker save` of the frontend image, read by `images.archive_identity`, gave the same config
digest as the image id. The sample manifest was built from this output. Registry digests are
recorded as `null`: this toolchain made no registry call. Observation only: during this work
the local assistant image acquired the tag
`ghcr.io/shaneqwaszx/clm-aws-demo-assistant:rc-d0142d8e8d74-e98a00b29851` and a repository
digest `sha256:4812bf8c...c44b7`, which means another session published it. That was not done
by this toolchain and the digest was not checked against the registry here. The tag is the
one `manifest.release_tag` computes.

`release.ps1 validate` on the sample rendered the `assistant` and `base` overlay sets offline
and passed; `release.ps1 baseline` confirms the reviewed baseline equals a fresh render of all
six overlay sets.

## 4. Independent review

**Verdict of the one independent review: FAIL** (P0 = 0, P1 = 3, P2 = 7, P3 = 9).

The reviewer was a fresh session that did not write the code. It reviewed commit
`728cf1ecda53ec81849329475cfc0ae3c72fdda7`, tree `c77a707565d45ccf00f3a0e071f43f287b34f4fb`.
Its report is reproduced **unedited** in
[INDEPENDENT_PIPELINE_REVIEW_20261114.md](INDEPENDENT_PIPELINE_REVIEW_20261114.md)
(SHA-256 `7f1fd794843a7ad6095fa468acebc1bb91a93f5a13e0c505b72ea60ee71cbd27`, byte-identical to
the file the reviewer wrote).

The findings were real. They were addressed afterwards by the implementing session. **That
remediation has not been independently re-reviewed.** Under `AGENTS.md`, changed reviewed
content needs a fresh independent review; until one returns `PASS`, the standing verdict on
this toolchain is `FAIL` and it must not be used against the host or the registry.

| Finding | Severity | What was done (not re-reviewed) | Test |
|---|---|---|---|
| F1 rollback of backend + frontend left ingress stopped and reported `ROLLED_BACK` | P1 | Rollback rewritten: with a backend, ingress is stopped first and started or recreated last; every step's return code is checked; it ends by confirming every service healthy and public `/health` 200, otherwise `FAILED_HELD` | `test_f1_*` (3), `test_m38_*` |
| F2 expiry between the pin and the first container change escaped unhandled | P1 | Restoring `compose.env` is housekeeping (no container touched), so it still runs after expiry; a stop raised while handling a stop is caught; a result is always written | `test_f2_*` (2) |
| F3 Docker-socket invariant blind to bind sources | P1 | The summary marks a socket by source as well as target; literal bind sources differ from the interpolated baseline | `test_f3_*` (2) |
| F4 summary too coarse; `cap_add` / `seccomp` declarable | P2 | Added command, entrypoint, health-check command, tmpfs, limits, `volumes_from`, bind-source kind; added capabilities and security options are invariants. Environment values, `extra_hosts` addresses and some other fields stay uncovered and are now listed in the architecture document | `test_f4_*` (10 cases) |
| F5 schema-19 rule bypassable by omitting or re-casing the commit | P2 | A compatible backend target must name a 7 to 40 character lower-case hex commit (schema and rule); the commit is normalised before the schema-19 check. Documents now say "declared", not "proved". The tool still cannot verify what an image writes | `test_f5_*` (7 cases) |
| F6 manual rollback overwrote `compose.env` wholesale, no host lock | P2 | It now changes back only this release's lines, only if they still show this release's pins (otherwise refuses and changes nothing), and takes the host lock | `test_f6_*` (2), `test_f7_*` |
| F7 rollback approval semantics | P2 | New `rollback` approval action, single use; the deploy approval is not accepted; `auto_rollback` is not required for an explicit rollback approval; runbook updated | `test_f7_*`, `test_owner_requested_rollback_*` |
| F8 interrupted run left no record | P2 | First fix (`e6356a1`): a record on interrupts inside the main run only. The re-review showed interrupts during failure handling, automatic rollback and owner-requested rollback were still unrecorded (N1, N2). Second fix: section 4.2. A record is written on every exit path **Python can catch**; a hard kill or power loss runs no handler, and then the last record on disk stands (during a rollback that is `ROLLBACK_IN_PROGRESS`) | `test_f8_*`, `test_rollback_interruption.py` |
| F9 undocumented `/etc/clm/mongo.uri`; fixed host paths | P2 | Host paths are configurable in the operator file; `--execute` refuses until `mongo_uri_file` is stated; checklist A5 is now an owner decision; the documents say the tool never creates the file. **Whether the file exists on the host is still unverified** | `test_f9_*` (2) |
| F10 surviving mutants, untested paths | P2 | Tests added for the 13 mutants the first review listed (M06, M23, M25, M28, M29, M33, M34, M38, M39, M42, M44, M47, M48) and for rollback of two services, expiry at the pin, interruption, and the GoldTier and provider overlays being active. The re-review then found 7 of its own 20 mutants surviving; those are addressed in section 4.2. `--transfer load` through `deploy.run` is still untested. Neither reviewer's full mutation run has been repeated by the implementer | `test_m*`, `test_rollback_interruption.py` |
| F11 weak deny-list | P3 | Quotes and backslashes are removed before matching; added `up` without `--no-deps` / `--no-build`, recreate flags, any `mongo` target, `exec`, direct `docker stop|exec|rm` forms. Still a backstop only | `test_f11_*` (17 cases) |
| F12 `--offline` with `--execute` | P3 | Refused; in execute mode a preflight check that could not be read is a failure | `test_f12_*` (2) |
| F13 `--skip-checks` left no trace | P3 | Every selected check is recorded `NOT_RUN` | `test_f13_*` |
| F14 missing document | P3 | This document | |
| F15 exit code 3 wording | P3 | Runbook corrected | |
| F16 pull script without `trap` | P3 | `trap` on EXIT, HUP, INT, TERM. Not executed on a real host. The SSH client timeout behaviour is documented, not changed | script assertion |
| F17 quoted `~` | P3 | Host state directory is now relative to the operator's home | `test_f17_*` |
| F18 destination starting with `-` | P3 | Refused | `test_m23_*` |
| F19 redaction scope; verify script writes a temp file | P3 | Redaction scope is in the credential guide. The scratch file `verify_host_firewall.sh` writes and removes (`/tmp/.clm_r3_check`) is now stated in `PIPELINE_ARCHITECTURE.md` section 2; no code change | |

Also fixed, found by the implementing session while running the toolchain on itself: the
`release-ruff` check lacked the documented lint options and failed; the assistant's in-image
comparison now covers the two `scripts` files the Dockerfile copies (99 files, the same count
as the coordinator's hand check); the image-store detection no longer mistakes a pushed
classic-store image for a containerd one.

The reviewer's section 5 (what cannot be assessed without a real host or registry) stands in
full and is not changed by the remediation.

### 4.1 Re-review of the F1 to F19 remediation

A second fresh reviewer re-reviewed head `7fa914637c452ada392739e818f06282afeb496e` (tree
`5a6754279844b1072bcc3ae4d5579fee69d0a4ed`): **PASS WITH NOTES**. It confirmed F1, F2 and F3
fixed, found no new P0 or P1, and raised two new P2 findings (N1, N2), six P3 notes (N3 to N8)
and four overstated statements in these documents. That report is held by the release
coordinator at `outputs/integration-release-lead-20261114/PIPELINE_REMEDIATION_REREVIEW.md` in
the main checkout; it is not reproduced here.

### 4.2 N1 and N2 (interrupted rollback), and the notes addressed with them

| Finding | What was done | Tests (`test_rollback_interruption.py`) |
|---|---|---|
| N1 (P2) an interrupt or error during automatic rollback left no record | `ROLLBACK_IN_PROGRESS` is written and flushed to disk before the first rollback step; each step is journalled before it is issued; any exception Python can catch during failure handling or rollback is recorded as `ROLLBACK_INTERRUPTED` with host state `unknown`, then re-raised. If the in-progress record cannot be written the rollback does not start | `test_in_progress_record_is_on_disk_before_the_first_rollback_step`, `test_interrupt_before_any_rollback_step_*` (3), `test_a_process_that_dies_without_any_handler_*`, `test_interrupt_after_ingress_is_stopped_*`, `test_interrupt_during_the_ingress_stop_itself_*`, `test_interrupt_during_service_replacement` (2), `test_rollback_is_not_started_when_its_in_progress_record_cannot_be_written` |
| N2 (P2) an interrupted owner-requested rollback left `DEPLOYED_AWAITING_ACCEPTANCE`, and `accept` would pass | The owner-requested rollback writes `ROLLBACK_IN_PROGRESS` before its first step and records an interrupt as `ROLLBACK_INTERRUPTED`; `accept` refuses (`ROLLBACK_INCOMPLETE`) while a rollback is in progress, interrupted or failed; a new read-only `recover` command is the only way back to an acceptable state, and only on what it verifies | `test_accept_is_refused_after_an_interrupted_owner_requested_rollback` (4), `test_manual_rollback_record_is_unacceptable_from_before_its_first_step`, `test_recover_*` (4), `test_incomplete_recovery_*`, `test_recovery_with_an_unreadable_host_*` |
| N3 (P3) no retry after a part-failed rollback | A repeated attempt is allowed with a new `rollback` approval; a line already on the previous pin is accepted; attempts are kept in `rollback_history` | `test_repeated_rollback_after_a_failed_automatic_one_*`, `test_repeated_manual_rollback_after_an_interrupted_one`, `test_first_manual_attempt_still_refuses_a_host_that_has_moved_on` |
| N4 (P3) automatic rollback ran after the host lock was released | Failure handling now runs inside the locked section | `test_automatic_rollback_runs_while_the_host_lock_is_still_held` |
| N5 (P3) flags set after a command returned | For rollback steps the intent and the ingress flag are recorded before the command is sent. The deployment path itself is unchanged: an interrupt during its first pin can still be recorded as `FAILED_NO_CHANGE` with the pin written (the record says the host is unverified only when the tool knows it touched it) | `test_interrupt_during_the_ingress_stop_itself_is_not_under_reported` |
| N6 (P3) seven surviving mutants | Tests added for all seven: rollback's final all-healthy and public health checks, failed ingress stop and failed backend stop during rollback, the rollback approval's single use, the skipped-preflight rule, and a stop raised while handling a stop | `test_rollback_is_not_complete_until_*` (2), `test_failed_rollback_command_*` (4), `test_a_rollback_approval_cannot_be_used_twice`, `test_execute_stops_when_a_single_preflight_check_could_not_be_read`, `test_a_stop_raised_inside_failure_handling_is_recorded_as_held` |
| N7 (P3) expiry between ingress stop and backend recreate | Not changed (expiry stops execution). Now stated as limitation 4e in the architecture document | |
| N8 (P3) socket invariant is a substring test; `manual_rollback` outside execute | Substring limit stated as limitation 4f. `manual_rollback` now refuses any mode but execute | `test_manual_rollback_never_runs_outside_execute_mode` |

The implementer's own spot mutation check on these safeguards: 16 mutants, each removing one
rule (the in-progress record, interrupt recording on both paths, the `accept` refusal, the
final verifications, the stop-failure checks, the skipped-preflight rule, single use of the
rollback approval, the early ingress flag, both `recover` conditions, the lock scope, the
retry rule): **16 of 16 killed** by `tests/release`. This is a targeted check written by the
implementer, not a repeat of either reviewer's mutation run.

### 4.3 Independent review of the N1/N2 change, and what was done about it

A third fresh reviewer reviewed commit `37f3aa6835c894d6efbe3fbff0a9bbf9a863008c` (tree
`7dcf54de74e1e8e7c402ad413cc9da435fdb791e`): **FAIL**. N1 and N2 were confirmed **fixed**
(378 automatic-rollback and 666 owner-requested-rollback interruption cases probed), but the
new `recover` step introduced one P1, and there were three P2 and seven P3 findings. The
report is reproduced **unedited** in
[N1_N2_INDEPENDENT_REVIEW_20261114.md](N1_N2_INDEPENDENT_REVIEW_20261114.md).

| Finding | What was done | Tests |
|---|---|---|
| 1 (P1) `recover` could return a deployment that stopped on a stop condition, or whose acceptance failed, to `DEPLOYED_AWAITING_ACCEPTANCE`, and `accept` then passed | The release's state when its first rollback began is recorded once (`state_before_rollback`) and kept across attempts. `recover` returns a release to awaiting acceptance only if it was in that state then; otherwise a host verified on the release is recorded `FAILED_HELD` / `RECOVERED_ON_RELEASE_NOT_ACCEPTABLE` and `accept` refuses | `test_recover_keeps_a_deployment_that_stopped_on_a_stop_condition_held` (3), `test_recover_never_turns_a_failed_acceptance_into_an_acceptable_release`, `test_the_origin_state_survives_repeated_attempts` |
| 2 (P2) a transient Windows "Access is denied" on the state-file rename aborted a rollback and made the suite flaky | The rename and the journal append are retried for about two seconds | `test_state_file_rename_is_retried_*`, `test_a_rollback_survives_transient_state_file_failures`. 12 consecutive full runs of `tests/release` after the fix: 12 of 12 passed |
| 3 (P2) owner rollback of a partly applied release ended `ROLLED_BACK` with a never-applied service still pinned to the release | The owner-requested path now changes back every line of the release that still shows its pin, and the final verification on both paths requires every line to show the previous pin | `test_owner_rollback_of_a_partly_applied_release_restores_every_pin`, `test_rollback_is_not_verified_while_any_release_pin_remains` |
| 4 (P2, claim) the ingress flag was not set when the frontend itself was recreated | Recreating the frontend sets the flag before the command; the sentence in the architecture document is corrected and scoped to rollback | `test_frontend_recreate_is_flagged_as_possibly_stopping_ingress`, `test_failed_owner_requested_rollback_reports_that_ingress_may_be_stopped` |
| 5 (P3) stale failure text in a verified record | Moved to `held_reason_before_recovery` | `test_recovered_record_does_not_keep_a_contradicting_failure_text` |
| 6 (P3) three interrupt windows not ending `ROLLBACK_INTERRUPTED` | The approval is now consumed inside the recorded section. The other windows are unchanged, conservative, and now stated in architecture 3.6 | `test_the_in_progress_record_exists_before_the_rollback_approval_is_consumed` |
| 7, 8, 9 (P3) host lock leak just after `mkdir`; `compose.env` restored after expiry before the rollback stops; record read before the local lock | Not changed. All predate this change or are conservative; the stale-host-lock step in the runbook covers the first | |
| 10 (P3) runbook wording | Corrected | |
| 11 (P3) nine uncovered mutants | Tests added for all nine (M07, M10, M11, M13, M21, M22, M24, M25, M33) | `test_recover_does_not_report_rolled_back_unless_everything_is_verified` (3) and others in the same file |

The reviewer could not reproduce the implementer's earlier "16 of 16 killed" for `recover`'s
previous-images branch; that claim was too broad (the mutant used made `recover` say "rolled
back" unconditionally, which is easier to kill than the reviewer's finer mutants). After the
tests above, the implementer's second spot check (15 mutants: the six fixes above and the nine
the reviewer named) is 15 of 15 killed. Both are the implementer's own targeted checks.

### 4.4 Check of the 4.3 fixes, and what was done about it

A fourth fresh reviewer checked commit `84706a97fe57d51ce9098518136181276d5d8080` (tree
`efbc61f242564894658ad4150fef3e5a05309cef`): **FAIL**. Findings 2, 3 and 4 were confirmed
fixed; finding 1 was **partly** fixed (the four original scenarios were held, as were 2,500
random call sequences, but one sequence still reached `ACCEPTED`). Its report is reproduced
**unedited** in [N1_N2_FIX_CHECK_20261114.md](N1_N2_FIX_CHECK_20261114.md).

| Finding | What was done | Tests |
|---|---|---|
| N-1 (P1) deploy, rollback interrupted, `recover`, `accept` fail, rollback interrupted, `recover`, `accept` pass reached `ACCEPTED`, because the origin was inherited across rollback episodes | The origin is kept only within one episode; a rollback that starts from `ACCEPTANCE_FAILED` has that as its origin. A failed acceptance is recorded permanently for that deployment and `accept` refuses it afterwards (see 4.5 for what "that deployment" means). `recover` also refuses to return a release that carries a stop code | `test_a_failed_acceptance_is_permanent_across_rollback_episodes`, `test_accept_refuses_a_release_that_already_failed_acceptance_whatever_its_state`, `test_recover_does_not_return_a_release_with_a_recorded_stop_code_to_acceptance`, `test_recover_does_not_return_a_release_marked_as_failed_acceptance_to_acceptance` |
| N-2 (P2) `ROLLED_BACK` recorded while a never-applied service ran the release image (after a manual `docker compose up`) | The final verification checks the container image, as well as the pin, of every service of the release | `test_rollback_is_not_verified_while_a_never_applied_service_runs_the_release_image` |
| N-3 (P2, older) a second `run`, including a dry-run, replaced an unfinished-rollback record | `run` refuses (`ROLLBACK_INCOMPLETE`) before writing or contacting anything | `test_a_new_run_never_replaces_the_record_of_an_unfinished_rollback` (2) |
| P3: wording on a persistent write failure; CLI did not print the held reason; four test gaps | Wording corrected; `recover` prints `held_reason` and the original stop code; tests added for the pre-check on never-applied services (2) and the journal-append retry | `test_first_attempt_accepts_the_previous_pin_only_for_a_never_applied_service`, `test_a_never_applied_service_on_neither_pin_refuses_the_rollback`, `test_journal_append_is_retried_after_a_transient_access_denied` |
| P3 not changed | Records written by the two intermediate commits are not migrated (the tool has never been used, so none exist outside tests); small edges in the retry helpers; the top-level `ingress_stopped` can lag `rollback.ingress_may_be_stopped` in a stale in-progress record (read the latter) | |

Implementer's spot check on these fixes: 10 mutants, 10 killed after the last test above was
added (9 of 10 before it).

### 4.5 Final check, and what was done about it

A fifth fresh reviewer checked commit `6bcf1423717ddd1f21e269c0394d8d0104345b23` (tree
`69e9f7b79663d8e00a8c4f9814ef8c7712d1b8a2`): **FAIL**, with an explicit condition. N-2 and
N-3 were confirmed fixed. For N-1 the reported sequence is closed, the intended positive path
still works, and 4,500 random sequences found no route to `ACCEPTED` through `recover`, an
interrupt, a failure, a stale record or a hand change. The verdict is FAIL because of F-1
below; the reviewer states that if a fresh verified deployment after a verified rollback is
meant to be acceptable, F-1 is a wrong sentence (P2) and the verdict would be PASS WITH
NOTES. Its report is reproduced **unedited** in
[N1_N2_FINAL_CHECK_20261114.md](N1_N2_FINAL_CHECK_20261114.md).

| Finding | What was done | Tests |
|---|---|---|
| F-1 (P1 as the rule was written) deploy, `accept` fail, owner rollback verified `ROLLED_BACK`, a **new** `deploy --execute` with a new owner approval, `accept` pass reaches `ACCEPTED`; the documents said a failed acceptance was permanent "for a release" | **The statement was narrowed, the behaviour kept.** This path is a new, complete, verified deployment under a new owner approval; it existed before this work, and forbidding it would change what an owner approval can do, which this remediation was told not to change. The failed acceptance is permanent for that deployment; a later deployment's record carries `previously_failed_acceptance: true`. **Owner decision recorded as open:** whether a release that once failed acceptance may ever be redeployed under the same release id | `test_a_new_verified_deployment_after_a_verified_rollback_carries_the_acceptance_history` |
| F-1, second part: a dry-run dropped `acceptance_failed` from the latest record | Fixed with F-2 | below |
| F-2 (P2) a second `run`, including a dry-run, replaced a `DEPLOYED_AWAITING_ACCEPTANCE`, `ACCEPTANCE_FAILED` or `FAILED_HELD` record with `FAILED_NO_CHANGE`, after which `accept`, `rollback` and `recover` all refused | A run that changes nothing is kept as a numbered result and no longer replaces the standing record of a live release | `test_a_run_that_changes_nothing_never_replaces_the_standing_record_of_a_live_release` (6) |
| F-3 (P3) after the new N-2 check fails, the never-applied service must be recreated by hand before a retry can succeed | Not changed; stated in the runbook | |
| P3 test gaps | Tests added for the refusal over a `FAILED_HELD` record whose rollback failed, and for the origin test inside `_may_return_to_acceptance` | `test_a_new_run_is_refused_over_a_held_record_whose_rollback_failed`, `test_recover_needs_the_awaiting_acceptance_origin_even_without_other_marks` |

### 4.6 Closing check

A sixth fresh reviewer checked commit `ed38d160c224aa4e6326ae15a0adfdb8e8d15ca2` (tree
`419b08f1deac6669961c420be97dc525ccd1d8a8`): **PASS WITH NOTES** (P0 0, P1 0, P2 1, P3 6).
F-2 confirmed fixed (8 reproduced cases; 5,773 no-change runs in a random driver never
replaced a live standing record). On F-1 the reviewer assessed the choice on its merits:
keeping the new-deployment path is consistent with "no change to deployment approval policy";
within one deployment a failed acceptance never reached `ACCEPTED` in 3,300 random sequences;
the owner decision stays open. Its report is reproduced **unedited** in
[N1_N2_CLOSING_CHECK_20261114.md](N1_N2_CLOSING_CHECK_20261114.md).

**This is the latest independent verdict on code. The commit after it changes documents
only** (this section and the corrections below) and was not itself reviewed.

| Note | What was done |
|---|---|
| N-1 (P2, claim) the documents said the owner "sees the history at acceptance time", but `accept`, the runsheet and `status` do not show `previously_failed_acceptance` | Statement corrected in architecture 3.7: the flag is in the record and the `deploy` output only. Showing it in `accept`, the runsheet and `status` is an **open follow-up** (a code change, so it would need its own check) |
| N-2 (P3) an interrupt at the instant of the first pin is recorded `FAILED_NO_CHANGE`; with a live standing record kept, `status` shows no trace | Not changed (the flag lag in the deployment path predates this work). Now stated in architecture 3.7 |
| N-3 (P3) "the record that describes the host" overstated | Wording corrected |
| N-4 (P3) the kept path does not strictly require a `ROLLED_BACK` record | Wording corrected |
| N-5 (P3) `_record` reads the standing record before each write with no retry; a read failure fails closed but can lose the attempt's record | Not changed |
| N-6 (P3) four surviving mutants (replacement of a non-live record, `DRY_RUN_OK` over a live record, `ACCEPTED` in the live set, the history-flag carry-over) | Not changed: open test gaps |
| N-7 (P3) wording; the runbook's hand command named `dc`, which cannot start the assistant | Runbook corrected to name the service's own wrapper |

### 4.7 Where the verdicts stand

| Commit | Content | Independent verdict |
|---|---|---|
| `728cf1e` | first candidate | FAIL (first review) |
| `7fa9146` | F1 to F19 remediation | PASS WITH NOTES (re-review; raised N1, N2) |
| `37f3aa6` | N1, N2 | FAIL (N1 and N2 fixed; new P1 in `recover`) |
| `84706a9` | fixes | FAIL (one sequence still reached `ACCEPTED`) |
| `6bcf142` | fixes | FAIL, conditional on the reading of one rule |
| `ed38d16` | fixes | **PASS WITH NOTES** (closing check) |
| head | documents only, after `ed38d16` | not reviewed (documents only) |

No reviewer has reviewed the whole toolchain at the head in one pass: the first review covered
everything at `728cf1e`, and each later review covered a delta. Nothing here is evidence from
a real host or registry.


## 5. What the evidence does not show

0. **A process that dies with no handler records nothing more** (SIGKILL, power loss,
   machine failure). During a rollback the last durable record is `ROLLBACK_IN_PROGRESS`,
   which is truthful; during the deployment itself it is the previous result or none. The
   tests simulate this by making the handler itself die; no real kill was performed.
1. **Nothing has run against the real host or registry.** Every host and registry behaviour
   is the behaviour of `tests/release/fakes.py`. The fake was written from the Approval B
   scripts and evidence, by the same author as the toolchain, so a shared misunderstanding of
   a real output format would not be caught. The first real use must be supervised
   (`FIRST_AUTOMATED_RELEASE_CHECKLIST.md`, steps D2, D3 and D6).
2. Remote shell snippets (the pull script, the sole-operator probe, `sed`, `ss` parsing) have
   not been executed by a real shell on Ubuntu.
3. The Windows Credential Manager wrapper was exercised with a throwaway entry only. No real
   token has been stored or used.
4. `docker login`, `docker push` and `docker buildx imagetools inspect` were never executed;
   their output formats are assumed from the earlier manual releases.
5. Archive transfer has no evidence on the host's containerd image store.
6. The risk classes and combined approvals are a proposal; no owner decision exists.
7. Local checks were proven to select and run; the long product suites were not run through
   the toolchain.
