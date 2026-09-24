# Industry-Standard Usage Ledger

Date reviewed: 2026-09-23

This ledger separates regulatory/industry guidance from technical implementation
methods. It does not convert a reference into sponsor policy, a business rule, or proof
of compliance.

| Source | Classification | Bounded use in this POC | Explicit non-use |
|---|---|---|---|
| [GLEIF LEI-CDF 3.1](https://www.gleif.org/content/4_lei-data/1_access-and-use-lei-data/2_level-1-data-lei-cdf-3-1-format/lei-cdf_version_3.1-documentation.html) and [GLEIF supporting documents](https://www.gleif.org/en/lei-data/access-and-use-lei-data/supporting-documents) | Industry data standard | Informs explainable entity-identity features such as official legal name, registry identifier, jurisdiction, legal form, addresses, status, and record dates. | No LEI lookup, GLEIF data ingestion, global identity authority, or name-only automatic match. |
| [ISO 17442 context through GLEIF LEI data access](https://www.gleif.org/en/lei-data/access-and-use-lei-data) | Industry identifier standard | Supports separating an identifier-plus-jurisdiction signal from fuzzy descriptive fields. | No claim that UEN is an LEI or that the POC implements ISO 17442 validation/certification. |
| [FATF guidance on beneficial ownership of legal persons](https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Guidance-Beneficial-Ownership-Legal-Persons.html) | Regulatory/industry guidance | Reinforces that beneficial-ownership evidence needs adequate, accurate, up-to-date information and cannot be replaced by a similarity score. | No new legal UBO rule; the existing deterministic Decimal engine remains authoritative. |
| [FATF Recommendations](https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Fatf-recommendations.html) | Regulatory/industry guidance | Provides high-level context for preserving human review and source evidence. | No autonomous approval, compliance conclusion, sanctions/PEP/adverse-media inference, or sponsor risk appetite. |
| [FATF risk-based approach for banking](https://www.fatf-gafi.org/content/dam/fatf-gafi/guidance/Risk-Based-Approach-Banking-Sector.pdf.coredownload.pdf) | Regulatory/industry guidance | Informs disclosure that real risk assessment depends on customer, jurisdiction, channel, product, transaction, and control evidence, much of which is absent here. | Missing signals are `NOT_ASSESSED`, never zero risk; the mock score is not a compliance decision and does not block readiness by default. |
| [NIST AI RMF 1.0](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10) | Voluntary AI risk framework | Informs versioning, reproducibility, explainability, limitations, evaluation, human review, and evidence around advisory models. | No claim of NIST certification or a production AI risk-management program. |
| [NIST SP 800-92](https://www.nist.gov/publications/guide-computer-security-log-management) | Technical security guidance | Informs bounded, access-controlled, integrity-aware, safe audit projections and retention terminology. | No claim that the POC event trail is a complete compliance/SIEM audit system. |
| [Fellegi-Sunter record linkage](https://doi.org/10.1080/01621459.1969.10501049) | Technical method | Informs transparent weighted agreements/disagreements and explicit uncertainty. | Not regulatory authority and not a justification for hidden probabilistic auto-linking. |
| [Splink parameter-estimation tutorial](https://moj-analytical-services.github.io/splink/demos/tutorials/04_Estimating_model_parameters.html) | Technical implementation reference | Informs reproducible synthetic evaluation and the distinction between model parameters and decision thresholds. | Splink is not added as a dependency, and examples are not copied as business rules or production model evidence. |

## Project application rules

1. Exact UEN plus country is the dominant exact-identity signal when both are present
   and non-conflicting.
2. Names, legal form, address, and dates are explainable supporting features. Name or
   address alone never causes automatic matching.
3. Missing evidence is explicit. It must not be treated as a negative fact or a zero
   risk signal.
4. Entity resolution, UBO advice, and mock risk outputs are versioned advisory
   projections with visible reasons and limitations.
5. Existing source evidence, deterministic ownership calculation, access control,
   human gates, and target ledger semantics retain authority.

## Implemented rule inventory

| Rule/default | Source concept | Implementation | Numeric source | Editable | Limitation |
|---|---|---|---|---:|---|
| Exact normalized registration identifier plus country dominates descriptive evidence | GLEIF/ISO identity attributes; project safety rule | `OnboardingIntelligenceService.resolve_entity` | none | no | UEN is not treated as LEI; conflict routes to review |
| Weighted name/address/legal-form/date linkage | Fellegi-Sunter-inspired technical practice | `entity-resolution-linear-v1` | weights are project-defined (`0.55/0.25/0.10/0.05/0.05`) | yes | deterministic probability proxy, not population calibrated |
| Auto-match/review/ambiguity thresholds | NIST-informed transparent governance; project decision | case-bound intelligence policy | project-defined (`0.85/0.60/0.03`) | yes | not an industry or sponsor constant |
| Name-only and address-only cannot auto-match; ties review | false-positive safety objective | entity-resolution owner | none | no | bounded current candidate set only |
| UBO advice consumes deterministic Decimal output | FATF BO evidence boundary plus current project owner | `ubo-advisory-linear-v1` | probability transform and `0.65/0.35` bands are project-defined | yes | never a legal UBO determination |
| Mock risk groups/bands | FATF RBA concepts | `mock-advisory-risk-rules-v1` | contributions and `30/60` bands are project-defined | thresholds yes | no PEP/sanctions/adverse-media/product/transaction source |
| Missing risk signals are `NOT_ASSESSED` | FATF/NIST evidence-quality principle | mock-risk result | none | no | not equivalent to low risk |
| Mock risk readiness review defaults off | Q-017 fail-safe boundary | `MOCK_RISK_BLOCKS_READINESS=false` in case snapshot | project-defined boolean | yes | explicit true routes only to human review; no compliance authority |
| Versioned model cards and synthetic evaluation | NIST AI RMF | `docs/models/*` and evaluation script | no borrowed threshold | no | synthetic scenario evidence only |
| Bounded safe activity CSV | NIST log-management minimization principle | authorized activity query/export | maximum 100 rows is project safety bound | query limit within bound | not regulatory retention or complete audit |
