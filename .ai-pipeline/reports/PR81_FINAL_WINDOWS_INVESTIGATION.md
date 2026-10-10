# PR #81 Windows health investigation

Disposition: **two complete isolated PASS runs; earlier loaded cause unresolved**.
The preserved prior failure returned HTTP 200 with complete headers/body in 9,234 ms
against the unchanged five-second monotonic deadline. It occurred alongside backend,
governance and browser verification. Resource contention remains a hypothesis.
No counterfactual proves contention, and no product correction is inferred from timing.

## Current evidence

Both complete original 31-test lifecycle suites ran alone, in separate Python processes,
in the genuinely fresh Windows checkout, under comparable idle conditions. No scenario
was excluded. The original five-second health budget, waits, assertions and lifecycle
timeouts remain exact. Only diagnostic wrappers recorded the original operations;
they added no retry, sleep, deadline or altered response. Detailed safe measurements,
UTC instants, process identities and lifecycle actions are in
`PR81_FINAL_WINDOWS_EVIDENCE.json`.

| Execution | Result | Wall seconds including final telemetry | Sampled CPU load | Available memory | Reset backend / frontend HTTP wall time |
|---|---|---|---|---|---|
| Isolated 1 | 31 PASS / 0 skipped | 357.195 | 3-27% | 10.10-10.67 GiB | 30.357 / 6.463 ms |
| Isolated 2 | 31 PASS / 0 skipped | 351.590 | 2-31% | 10.26-10.78 GiB | 21.735 / 23.070 ms |

The health records separate header acquisition and body read wall time, HTTP status
and the actual remaining budget. Launcher/listener PID, creation time and executable
identity checks remain those of the original suite. Start, stop and reset events retain
healthy-return timestamps and safe process metadata. Lightweight pressure sampling
records task-path processes without command lines or credentials; lifecycle identity
records cover the owned trees. No other verification suite ran during either execution.
Both suites cleaned their active launcher metadata before completion.

## Resource and checkout reconciliation

All three PIDs in the prior stopped session were absent. Its stale active metadata was
retained byte-exact in the task's ignored retention path before startup. No process was
killed during that reconciliation. The retained Docker container's exact ID and task
label were verified; it remained stopped throughout these Windows runs.

The fresh clone used command-scoped long-path support before checkout; raw-byte
comparison disabled command-scoped CRLF conversion. All 412 publication raw hashes and
all 785 committed report blobs verified before the exact eight corrections were copied.
The original worktree's 785 historical raw report hashes remain immutable. Earlier
FAIL reports remain unchanged. No persistent host Git configuration changed.

## Limits and next gate

No controlled loaded comparison was run: it is unnecessary for the current stability
claim, and this investigation does not claim a contention root cause. The earlier
single loaded failure remains unresolved evidence. The disposition is to serialize
all heavy verification and obtain a fresh independent assessment after every mandatory
current gate passes. A required subsequent failure still blocks release. This report
does not extend SDQ-01 risk acceptance, waive a current check or inherit an earlier PASS.
Source correction identity remains `fcddc61073095c8fcc2b09051ae626581499b02fa608d22ca144fcc8fc0bcc38`.
