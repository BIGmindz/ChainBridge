# PDO Explainability Standard

Version: v1
Status: CANONICAL

Authoring Agent:
- Agent: Maggie
- GID: GID-10
- Role: ML & Applied AI Lead
- Color: 💗 Pink

Applies To:
- ChainBridge Gateway
- PDO Lifecycle
- ChainIQ Risk Decisions
- Operator Console (OC)

Governance:
- CCDS v1: ENFORCED
- CALP v1: ENFORCED
- Gateway Contract v1: REFERENCED

Scope: All Proof of Decision Outputs (PDOs) emitted by ChainBridge decisioning or orchestration services.
Constraints: Glass-box only; no black-box scores; no opaque embeddings.

## Gateway Contract Alignment
- PDOs are issued only by the ChainBridge Gateway.
- Explainability requirements assume Gateway validation has occurred before emission.

## Objectives
- Provide regulators and auditors with transparent, reproducible decision evidence.
- Give operators high-confidence, human-readable context for actions taken or denied.
- Enable machine-verifiable integrity so downstream services and auditors can trust and replay decisions.

## Core Principles
- Deterministic and replayable: same inputs yield the same PDO.
- Full lineage: every input, transform, feature, and model/ruleset version is recorded.
- Signed and hashed: canonical JSON is hashed and signed with key metadata.
- No hidden logic: every contributor is visible; embeddings are only allowed with full dictionaries/decoders.
- Human-first: always include concise, non-jargon narratives and next steps.

## Required Fields — Regulatory Explainability
- **Identity & timing**: `pdo_id`, `schema_version`, `created_at` (UTC), `issuer` (service + model/ruleset revision), `request_id`, `tenant_id`.
- **Decision statement**: outcome, state, and timestamps in plain language.
- **Legal/policy basis**: policy/control IDs, jurisdiction tags, enforcement mode, effective dates.
- **Inputs used**: list of features/observations with name, value, unit, source, acquisition time; include redaction flags.
- **Attribution & rationale**: deterministic rule trace or feature contributions with direction (+/−) and magnitude.
- **Evidence artifacts**: hashes and URIs for documents/logs/proofpacks; retention horizon.
- **Model/ruleset card linkage**: pointers to model card or ruleset manifest (training window, assumptions, limits).
- **Governance metadata**: ALEX rule IDs hit, approvals/escalations, reviewer identities, segregation-of-duty markers, approval timestamps.
- **Risk & impact**: risk tier, impacted parties/systems, mitigations applied.
- **Cryptographic integrity**: canonical hash, signature, signing key ID, algorithm, signature timestamp, TTL.

## Required Fields — Operator Trust
- **Operator narrative**: concise, plain-language narrative linking inputs to outcome and what changed.
- **Top drivers**: ordered list (max 5) of factors with label, unit, direction, and contribution.
- **Actionability**: remediation/override guidance with concrete steps or thresholds to clear holds.
- **Data lineage**: source labels (first/third-party), freshness, completeness; call out missing or imputed data.
- **Confidence signals**: calibrated confidence bucket and numeric value, with validation window noted.
- **Safety/fairness checks**: bias/guardrail checks executed plus pass/fail or not-run-with-reason.
- **Traceability**: correlation IDs and links to audit/monitoring views.

## Human-Readable Requirements
- Plain English only; avoid model jargon and abbreviations.
- Consistent units, corridor labels, currencies, and UTC timestamps with timezone suffix.
- Provide ordered lists for drivers and rule traces; do not expose raw JSON walls to operators.
- Include an "ELI5" one-liner describing the primary rationale.

## Machine-Verifiable Requirements
- Canonical JSON with deterministic field order; include `schema_version` and validator version.
- Hash the canonical JSON (`canonical_hash`) and sign it; include `signing_key_id`, algorithm, and signature timestamp.
- Emit `evidence_ptrs` as content-addressed hashes/URIs; avoid embedding opaque binaries.
- Record feature-store version, data quality flags (missing/imputed/late), and deterministic seeds for replay.
- Log validation outcome (`pass|fail|not_run`) with validator version and time.

## Prohibited (Never Infer or Hide)
- No inference of protected attributes or proxies (e.g., race, religion, gender identity), and none may influence decisions.
- No opaque embeddings or latent vectors unless the full vocabulary/decoder is present in the PDO.
- No undisclosed manual tweaks; every override requires actor, reason, and timestamp.
- No hidden inputs: every feature considered must be listed, even if null/unused.
- No silent defaults or redactions: defaults and redactions must be explicit with reason and owner.
- No aggregated-only disclosures: list each contributing rule/factor; do not collapse into a single score.

## Minimal PDO Structure (canonical JSON view)
- `pdo_id`, `schema_version`, `created_at`, `issuer` (service, model_id, revision), `request_id`, `tenant_id`
- `decision` (type, outcome, state, timestamps, human_summary)
- `legal_basis` (policy_ids, jurisdiction, effective_dates, enforcement_mode)
- `inputs` (features_used: name, value, unit, source, acquired_at, redaction_flag, quality_flag)
- `rationale` (rule_trace | interpretable_feature_contribs with direction and magnitude)
- `evidence` (artifacts: uri, hash, type, retention_horizon)
- `model` (model_id/ruleset_id, version, checksum, training_data_window, feature_store_version)
- `governance` (alex_rules, approvals, reviewer_id, approved_at, sod_refs)
- `risk` (tier, impacted_parties, mitigations, controls)
- `operator_view` (narrative, top_drivers[], actionability, lineage, confidence, safety_checks, what_changed, contact)
- `trace` (correlation_ids, monitoring_links, lineage references to proofpacks/payment intents)
- `integrity` (canonical_hash, signature, signing_key_id, algorithm, signature_ts, ttl)
- `validation` (schema_version, validator_version, result, validated_at)

## Validation Checklist (must pass before emission)
- Schema validation success for declared `schema_version`.
- Deterministic serialization verified; signature matches `canonical_hash`.
- All required fields present; no disallowed opaque constructs detected.
- Redactions/defaults flagged with reason and owner.
- Operator narrative and drivers present and free of jargon.
- Timestamps normalized to UTC; units and currencies specified for quantitative values.
- Links to model card and governance artifacts resolvable.
- Fairness/guardrail checks recorded (result or not-run with reason).

## Versioning & Stewardship
- Bump `schema_version` on any breaking change; document migrations.
- Record model/ruleset revisions and deployment IDs per PDO.
- Archive validation results with each PDO for audit replay.
- Maintained by Maggie (GID-10); changes require governance review via ALEX rules.
