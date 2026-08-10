---
name: sponsor-contract-reconciliation
description: "Reconcile conflicting Delta Capita sponsor artefacts, GoldTier/EDS contracts, ACRA evidence, examples, mappings, and project decisions. Use for contract analysis, schema or mandatory-field conflicts, sponsor clarification intake, discrepancy cataloguing, quarantining invalid examples, and decision-log or open-question updates without silent assumptions or secret disclosure."
---

# Sponsor Contract Reconciliation

Apply the source-of-truth policy in AGENTS.md; do not create a competing authority in
this skill.

## Gather only relevant evidence

1. Read AGENTS.md, docs/PROJECT_CONTEXT.md, the active planner, and the relevant
   sections of:
   - docs/decisions/DECISION_LOG.md;
   - docs/contracts/GOLDTIER_CONTRACT_BASELINE.md;
   - docs/contracts/GOLDTIER_CONTRACT_DISCREPANCIES.md;
   - docs/contracts/ACRA_CANONICAL_MAPPING.md when ACRA is involved;
   - docs/sponsor-questions/OPEN_QUESTIONS.md.
2. Inspect only sponsor artefacts necessary for the assigned question and only when
   repository policy authorizes it. Do not open or use the quarantined authentication
   collection. Never reproduce credentials, tokens, keys, certificates, confidential
   customer data, or raw sensitive payloads.

## Reconcile

1. Compare endpoint paths, methods, headers, schemas, required fields, identifiers,
   enums, examples, mappings, auth/TLS assumptions, error behavior, and status semantics.
2. Apply the AGENTS.md hierarchy exactly: latest recorded direct sponsor clarification;
   corrected standalone operation OpenAPI for machine structure; sponsor-directed
   artefact for its specifically delegated question (including the provisional
   mandatory-field overlay); validating examples as reference only; combined bundle and
   other supporting evidence at their recorded confidence.
3. Label every conclusion as sponsor-confirmed, project-confirmed, provisional project
   decision, candidate/supporting evidence, unresolved, or invalid/quarantined. Use
   references/evidence-classification.md for the evidence record.
4. Treat an example that contradicts the provisional canonical contract as
   INVALID / QUARANTINED. Do not use it as a fixture, enum source, DTO model, mapping
   assertion, or evidence that the sponsor corrected another artefact.

## Record without guessing

1. Add every material conflict to
   docs/contracts/GOLDTIER_CONTRACT_DISCREPANCIES.md or the relevant contract mapping.
2. Update docs/decisions/DECISION_LOG.md only when evidence resolves a question or
   clearly establishes a provisional project decision; preserve the status distinction.
3. Add or refine unresolved sponsor/API-owner questions in
   docs/sponsor-questions/OPEN_QUESTIONS.md. Do not mark a question resolved without
   authoritative evidence.
4. If ambiguity would change implementation, validation, security, or a user-visible
   claim, stop that dependent work and report the blocker. Never choose a convenient
   interpretation silently.
5. Report evidence inspected, reconciled conclusion, discrepancies, document updates,
   quarantines, implementation impact, and remaining questions without sensitive values.
