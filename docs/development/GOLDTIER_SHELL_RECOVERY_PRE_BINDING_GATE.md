# GoldTier uncertain Shell recovery pre-binding gate

## Verdict: PASS

Date: 2026-10-01. Fresh independent read-only review. The first recovery Search
provides sufficient identity evidence to proceed with the one remaining authorized
exact-ID Search through the existing recovery owner. Local binding may occur only
if that second response verifies the identity under the reviewed checks below.
This is not a completed recovery verdict or permission for any provider mutation.

## Reviewed identity and authority

Original case `9d9c2542-5dfa-4343-bc73-2f65126b4a2c`; submission
`b26fdb74-6b81-4b0d-ae55-e22d80d05163`. The latest explicit user recovery authority
permits at most two read-only Searches; no Shell replay, Policy, Amend, deletion,
cleanup, Garden, Production/PingFed or new-customer operation.

The prepared plan's original pending-authorization field and earlier pending report
are historical preparation records. Current authorization comes from the subsequent
explicit user instruction; those historical records are not retrospectively relabelled.
Prior final acceptance FAIL, Shell uncertainty and all historical gates remain intact.

Reviewed frozen submission, plan/preflight, first Search receipt, read harness,
new exact-ID binding harness and current `recover_uncertain_shell_from_provider`
owner. Source V3, final 105-path review and 103-path evidence freezes still match
their recorded raw hashes. No reviewed implementation changed.

Exact pre-binding evidence identities:

| File | SHA256 |
|---|---|
| `tmp/GOLDTIER_SHELL_RECOVERY_FROZEN_PLAN.json` | `80edb1772c1c66795f51f09a7bc97ee63e8b7de331ced73cb1a72f72ea8e3626` |
| `tmp/GOLDTIER_SHELL_RECOVERY_PREFLIGHT.json` | `d2cd30f40c5c263552c7f05b675e983e2a6a41a2c94115990ca3bfa4face972d` |
| `tmp/GOLDTIER_SHELL_RECOVERY_READ_RECEIPT.json` after Search 1 | `0fc42279a74e82b06e2f94116c81dda854c521eff5fb4a39c3c2916c94ce25f3` |
| `tmp/goldtier_shell_recovery.py` | `cd248f104fad2a19b415c7ccf24cdb9b331a221963e7ef410a9d1ab05ae6462f` |
| `tmp/goldtier_shell_recovery_bind.py` | `217e77c3e9f2217d4bd6206c47426d0786dc0f564aa27b0802b7c29c6ed17780` |

These identities describe the reviewed pre-binding state. The authorized second
Search/local binding will necessarily append later evidence to the recovery receipt;
it must not overwrite the original provider-attempt history.

## Identity evidence assessment

Chronology is original HTTP 200 NO_MATCH, exactly one transport-uncertain Shell,
then one recovery Search using the exact frozen high-entropy synthetic legal name
and SG incorporation-country filter. Recovery Search 1 returned HTTP 200 MATCH_FOUND,
exactly one candidate, ID `143880`, with an exact normalized legal-name match.

The provider projection returned only `party_id` and `legal_name`. Registration,
country, legal form, address and external reference were absent. There is no optional
field mismatch, but none of those absent fields is proved by the response. SG is
the query filter, not a claimed returned field. This evidence is sufficient for the
bounded POC verification step when combined with the frozen identity and original
attempt chronology; it is not legal identity certification or proof that the original
Shell HTTP response succeeded.

The first read left Mongo unchanged: preflight/read hashes agree at
`13e6794c8ad857c22b62404895cc6ab8a2bfb87052f8c29eec379e58b039065e`.
The case remains the same unresolved durable intent before binding.

## Exact-ID and local binding conditions

The reviewed new binding harness consumes Search 2 through the existing owner,
using only GET of the same direct Sandbox Search path with `goldTierID=143880`.
It rejects a third Search and every provider mutation, saves the attempt before
transport and uses the actual connector/decoder without Mock result substitution.
Settings keep writes disabled. It uses existing Mongo repository constructors and
does not initialize stores, create indexes, bootstrap administration or clean data.

The owner requires the exact frozen case/submission identity, retained IN_PROGRESS
SEARCH,SHELL history, no resolved provider ID and a permitted uncertain origin. It
performs the fresh exact-ID Search before its local persistence boundary. Its native
response check requires one candidate with the same ID and exact legal name.

The additional `checked_search` wrapper verifies every projected safe optional
identity field through the current `_readback_identity_matches` helper, and requires
non-null exact normalized legal name, before returning the real response to the
owner. This closes the owner-only ID/name comparison limit without changing owning
source or fabricating absent fields. Wrong/multiple/absent ID, wrong name, optional
field mismatch, failure or malformed response must stop without binding.

If verified, the existing owner may record PROVIDER_VERIFIED_RECOVERY, retain the
ID locally and preserve original attempted SEARCH,SHELL, original completed SEARCH
and original uncertain-outcome chronology. Subsequent provider verification resolves
the local recovery fact; it does not rewrite the original Shell as a successful HTTP
response. No terminal submission success, Policy/KYC initiation, Amend or approval
may be inferred. Separate fresh-process persistence/restart evidence and independent
final recovery review remain required afterward.

## Checks and scope

Independent focused existing recovery-owner tests: six PASS with dotenv disabled,
memory/mock test settings and Mongo construction forbidden. They cover recovery
without replay, identity rejection and fail-closed provider evidence. Source/evidence
freeze and reviewed harness hashes matched before and after this review; report
secret/whitespace checks passed. No provider call or Mongo write/initialization was
performed by the reviewer. No private artifact, authentication value, `.env`, URI
or raw payload was disclosed. Only this assigned report was written.

Remaining authorization is one exact-ID Search and conditional local binding only.
All provider writes remain zero; any later continuation requires separate authority.
