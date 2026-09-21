# Phase 18 case portfolio — reflection

The vertical slice remained inside the established query/repository/cache owners. The
most important self-review finding was not in the new route: session prefetch still used
the compatible unbounded array endpoint. Migrating that caller made the bounded outcome
real rather than cosmetic.

The strict Mongo facet deliberately validates all authorized projected candidates before
filtering. This costs more than validating only returned rows, but prevents malformed
in-scope data from disappearing into a false partial page. Scope remains the first match,
so another team's corruption cannot influence an ordinary actor. The design therefore
chooses trustworthy bounded output over an unsupported scalability claim.

The first independent gate proved that projection itself can erase a malformed optional
container before projected validation sees it. The repair computes a bounded validity
marker on the three projected optional source containers before projection and evaluates
that marker with the projected validator inside the same aggregation. The same gate also
exposed that Python full `casefold()` was broader than Mongo regex matching. Search now
uses one explicit escaped ASCII-case-pair contract in both adapters and regression-tests the
`ß`/`ss` non-equivalence, avoiding a false parity claim without adding a search engine or
schema field. A second gate then showed that Python and PCRE also disagree on dotted and
dotless I even under their simple modes. The final design removes both engines from the
semantic decision: ASCII letters are explicit paired classes and every non-ASCII code
point is literal. This smaller contract is deterministic, sufficient for UEN/UUID case
normalization and ordinary ASCII corporate-name casing, and honest about its Unicode
limit.

A third independent gate closed both data/query defects but found the new route had not
adopted the established stable persistence-error projection. The bounded repair catches
only the three expected persistence exception types and returns one fixed 503 code and
message. It neither hides an empty page behind corruption nor broadens the catch to mask
unexpected programming failures.

Browser corpus setup initially exercised too many protected writes and obscured the read
behavior. Moving synthetic setup to a test-only bounded application seam through the
canonical orchestrator retained realistic product requests while making the acceptance
repeatable. The final browser still proves real authentication, network, cache, mutation,
route, and DOM behavior.

No sponsor or architecture question was answered implicitly. Offset paging, lack of an
index/total/snapshot, literal search, and Mock/Local provider classifications are explicit
limits. Independent review must now challenge scope-first validation, Mongo/memory parity,
query identity, deletion races, test-only fixture containment, and the truthfulness of
the performance claims before publication.
