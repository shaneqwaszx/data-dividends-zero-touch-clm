# GoldTier Uncertain Shell Recovery

Status: PROVIDER_VERIFIED_RECOVERY persisted and confirmed in a fresh process.
Independent final recovery gate is recorded separately in
`GOLDTIER_UNCERTAIN_SHELL_RECOVERY_GATE.md`; no later provider operation is authorized.

## Original State

Branch `fix/demo-happy-path-stabilization`; HEAD/base/local origin main
`efc31f450f0103766fa812bc0aa80754f801dbe9`; staging empty. The accepted uncommitted
candidate and all historical manifests, evidence and independent gates are preserved.

Case `9d9c2542-5dfa-4343-bc73-2f65126b4a2c`; submission
`b26fdb74-6b81-4b0d-ae55-e22d80d05163`. Original Search: HTTP 200 NO_MATCH.
Original Shell: exactly one dispatch, transport-uncertain, no returned GTID.
Policy/Amend: never dispatched. The original acceptance receipt remains unchanged.

## Recovery Activity

The user's subsequent explicit authorization allowed two read-only recovery Searches
for this exact frozen identity. The pending preparation record is retained unchanged;
it is superseded only for authorization by that explicit instruction.

Search 1: GET current direct XPI Sandbox Search, exact frozen legal name
`FYP SYNTHETIC ACCEPTANCE FA2948FE1BE5` plus `countryOfIncorporation=SG`.
Dispatched `2026-10-01T02:17:17.583853+00:00`; HTTP 200 MATCH_FOUND, exactly one
candidate, ID `143880`, exact normalized synthetic legal name.

Independent pre-binding gate: PASS, SHA256
`261296c7bb592d41dd777d4102371b6d2f435550335b22c4c9c8fb35ab6b88c5`.

Search 2: exact `goldTierID=143880` verification dispatched by the existing
`OnboardingService.recover_uncertain_shell_from_provider` owner.
Dispatched `2026-10-01T02:21:46.468969+00:00`; HTTP 200 MATCH_FOUND, exactly one
candidate, same ID and exact name. All projected optional identity fields were
checked before the actual response was returned to the recovery owner.

Authorized budget consumed: 2/2. No third request. The NO_MATCH wait/repeat branch
was not used because Search 1 returned a unique sufficiently bound candidate.

## Candidate Evidence

Both responses projected only `party_id` and `legal_name`. Registration number,
country, legal form, address and external reference were absent and remain unproved
by provider response. SG is the frozen query filter, not a returned-field claim.
The retained recovery registration/country are frozen case identity bindings, not
new provider evidence. No raw provider payload, header, credential or URI is retained.

Chronology: original NO_MATCH -> one transport-uncertain Shell -> unique exact frozen
synthetic-name Search -> independent pre-binding PASS -> fresh exact-ID verification.
This proves the bounded recovery identity; it does not rewrite the Shell HTTP result.

## Durable Ledger

| Field | Before | After recovery and fresh-process read |
|---|---|---|
| Owning case/submission | Original exact identities | Unchanged |
| State | IN_PROGRESS | IN_PROGRESS |
| Attempted operations | SEARCH,SHELL | SEARCH,SHELL |
| Definitively completed | SEARCH | SEARCH |
| Lifecycle resolved | SEARCH | SEARCH,SHELL |
| GTID | None | 143880 in case and ledger |
| Shell status | Unresolved | PROVIDER_VERIFIED_RECOVERY |
| Original outcome uncertain | Transport evidence | true retained |
| Replayed | No replay | false |
| Policy/Amend status | None | None |
| Terminal outcome/receipt | None | None |

The normal recovery owner persisted the existing ledger through its Mongo repository
and retained the ID on the original case. No alternative persistence/recovery owner,
initialization, administrative bootstrap, index creation, reset or cleanup was used.
The bind process exited; a new process loaded the same retained Mongo case and ledger
through normal repositories with zero provider requests and zero database mutations.
The service remains running; its exact container running-state flag was true.

Original document SHA256:
`13e6794c8ad857c22b62404895cc6ab8a2bfb87052f8c29eec379e58b039065e`.
Post-recovery and both fresh-read hashes:
`fb11ed2085b234ae83eaba4d97247b994f6e48617f4ee6b2224e184883a7574f`.
Only the allowlisted retained disposable database was used; normal Atlas was not accessed.

Evidence: `tmp/GOLDTIER_SHELL_RECOVERY_READ_RECEIPT.json`,
`tmp/GOLDTIER_SHELL_RECOVERY_RESTART_PROOF.json`, original preflight/frozen plan,
and the new task-owned guarded read/bind/restart harnesses.

## Recovery Classification

PROVIDER_VERIFIED_RECOVERY. GTID `143880` is retained from subsequent provider
verification. Original Shell remains transport-uncertain and definitively completed
operations do not include Shell. No completed full submission, Policy, KYC or approval
is inferred from Search recovery.

## Replay Safety

Recovery Search 2/2; Shell replay 0; Policy 0; Amend 0; related parties 0;
Garden 0; Production/PingFed 0; new customer lifecycle 0; deletion/cleanup 0.
Provider writes remained disabled throughout. No Git mutation/publication occurred.

## Independent Recovery Gate

Pre-binding independent gate: PASS. Final fresh independent recovery review is
recorded in `GOLDTIER_UNCERTAIN_SHELL_RECOVERY_GATE.md`; it must assess the exact
frozen recovery evidence and actual retained ledger. Prior acceptance FAIL remains
historical and is not relabelled as full provider acceptance.

Local focused recovery/no-replay checks: 7 passed, 95 deselected, memory/mock only,
dotenv disabled and Mongo construction forbidden. New task harnesses compile;
Git diff whitespace check passed. Existing application source and tested candidate
remain unchanged; broad acceptance checks were not unnecessarily repeated.

## Final State

GOLDTIER SHELL: RECOVERED through provider verification; original transport UNCERTAIN.

GOLDTIER ID: RETAINED (`143880`), original case/submission.

POLICY: NOT EXECUTED.

GOLDTIER FULL POC SUBMISSION: PENDING; later provider work requires a new instruction.

MONGO ACCEPTANCE LEDGER: PRESERVE; service remains running.

No API/type, schema, connector, configuration, business rule, mapping, auth/security,
architecture or provider classification changed in this continuation. Runtime data
changed only through the existing provider recovery path on the original synthetic
case/ledger; the full external-demo acceptance remains partial pending Policy and
remaining authorized lifecycle acceptance. No commit, push, PR or merge occurred.
