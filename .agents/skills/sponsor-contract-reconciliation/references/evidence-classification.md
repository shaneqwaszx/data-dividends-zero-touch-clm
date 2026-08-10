# Contract evidence classification

Use this compact record for each material conclusion or conflict.

| Field | Required content |
|---|---|
| Question | The precise endpoint, field, enum, behavior, mapping, auth, or TLS issue |
| Sources compared | Artefact names and relevant operation/section; never secret values |
| Observed difference | Each conflicting form without implying correction |
| Applied authority | The applicable `AGENTS.md` hierarchy rule |
| Classification | Sponsor-confirmed, project-confirmed, provisional project decision, candidate/supporting evidence, unresolved, or invalid/quarantined |
| Canonical development treatment | What current mock/implementation/tests may use |
| Prohibited use | Quarantined examples, stale values, or unconfirmed claims that must not propagate |
| Confirmation needed | The exact sponsor/API-owner question and affected phase |
| Files updated | Discrepancy catalogue, decision log, open questions, baseline, or mapping document |

Keep sponsor-confirmed facts distinct from project decisions made to permit safe
development. An explicit sponsor direction about which artefact answers a question is
confirmed; the derived overlay may still be provisional when sources remain
structurally inconsistent.
