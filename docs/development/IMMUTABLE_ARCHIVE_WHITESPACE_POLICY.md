# Immutable archival whitespace publication policy

The PR81 owner expressly authorized this policy on2026-10-11 after the native staged
check failed. It applies through scripts/pre_pr_check.py, the canonical pre-PR owner.
It does not alter Git whitespace semantics or the original native exit status.

Retain the25 historical TCP helper/SOP archives: seven immutable reviewed bundles and
five procedure/handoff records require their actual bytes to independently recompute
historical manifest/review provenance. Removing them would leave published historical
identity claims without their authoritative content. They are frozen evidence, not
maintained runtime owners; custom tracing expansion remains stopped.

HISTORICAL_ARCHIVE_EOF is the complete approved25-path registry. Each record binds the
exact repository path, raw UTF-8 blob SHA256, exact terminal logical-line number and
HISTORICAL_EVIDENCE classification. The checker validates record shape, path, hash,
line type and classification, then raw-byte identity and exactly one final empty logical
line. Mixed original LF/CRLF is preserved. Only the exact native diagnostic
new blank line at EOF. at that bound location may be dispositioned, once per path,
and only for native exit2. Changed bytes, extra blank lines, unsupported paths or
locations/types, malformed records and other errors continue failing.

The existing HISTORICAL_PATCH_WHITESPACE policy independently binds the two PR81
archival diffs and three exact single-space context alerts. Existing earlier patch
records remain unchanged. It is separate from the25 EOF records.

For this unchanged archive set, native Git returns2 with28 diagnostics:25 EOF plus3
context. Record native failure and canonical-policy acceptance separately. Never label
native Git exit2 as a native PASS. New source/document whitespace is not exempt.

The exception exists solely to publish immutable historical evidence without altering
its reviewed bytes. Any future record addition/removal/change requires separate owner
scope, focused adverse checks and fresh independent review. The policy retires only if
all associated evidence/provenance is explicitly retired or separately dispositioned;
never trim frozen files or widen a path/hash/diagnostic rule incidentally.
