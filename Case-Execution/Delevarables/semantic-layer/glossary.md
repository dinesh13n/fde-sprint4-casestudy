# Glossary

Synthetic data. Terms are parsed by `tools/build_json.py`; every entity id must appear here.

| Term | Definition | Source |
|---|---|---|
| Case | A unit of quality-operations work: a batch-quality review / deviation-handling case that moves through a review lifecycle and may end in a human batch-disposition decision. | docs/11-data-context/knowledge-model.md |
| Batch | A manufactured batch of a material whose quality is under review. | docs/data-dictionary.md |
| Material | A pharmaceutical material/product type that batches are made from. | docs/data-dictionary.md |
| LabResult | A laboratory test result for a batch; may be pending, valid, invalid or out of specification (OOS). | docs/domain-contracts.md |
| Deviation | A recorded departure from the expected manufacturing/quality process for a batch, with a classification and an optional root cause. | docs/domain-contracts.md |
| CAPA | Corrective And Preventive Action raised to address a deviation, with an owner and a due date. | docs/domain-contracts.md |
| SOP | A Standard Operating Procedure version with an effective window. | docs/domain-contracts.md |
| ReferenceVersion | Versioned master/reference value with an overlapping validity window; requires temporal interpretation (which version applied at time T). | docs/partner-feed-operations.md |
| Site | An operating site, referenced by cases and batches through local aliases. | docs/11-data-context/knowledge-model.md |
| DecisionEvent | An immutable, hash-chained fact about a case: a state change, evidence attachment, human disposition, override or correction. | docs/12-specs/contracts/ddl/hub-schema-v0.1.sql |
| CaseState | The current state of a case, derived by folding its DecisionEvents. | docs/12-specs/contracts/ddl/hub-schema-v0.1.sql |
| EvidenceRecord | A reference to something relied on for a decision: a document, an intake item, a crosswalk object or an external reference. | docs/12-specs/contracts/ddl/hub-schema-v0.1.sql |
| ZoneHAction | One of ten closed, human-only actions (ZH-01..ZH-10) that automation may never perform: batch disposition, QA release, e-signature record, close-exception, policy adopt, rule-set activate, exception-rule accept, disposition-mode change, schedule enable/disable, policy change. | docs/12-specs/features/f02-human-disposition-gate.md |
| PolicyObject | A versioned, owned, effective-dated statement of business meaning: a definition of closed/resolved/approved, a clock (e.g. | docs/12-specs/features/f03-policy-definitions-rule-service.md |
| PolicyEvent | Immutable record of a change to policy state (created, adopted, accepted-open, withdrawn, rule row changed, rule set activated, etc.) with old value, new value, actor and a mandatory authority reference. | docs/12-specs/contracts/ddl/hub-schema-v0.1.sql |
| RuleSet | A named, versioned, table-driven set of approval/priority rules where thresholds, regions, effective dates, owner and default behaviour are DATA. | docs/12-specs/features/f03-policy-definitions-rule-service.md |
| RuleRow | One ordered row in a rule set: conditions (field/op/value), an outcome, an effective window, an owner and an is-default flag. | hub/policy/rulesets.py |
| RuleTrace | Text explanation of one rule evaluation for a case: rule set, row and inputs. | docs/20-application/state-model.md |
| SourceSystem | An upstream system or partner feed: ElectronicBatchRecord (publishes OOS_RESULT, DEVIATION, CAPA_UPDATE), LIMS-QMS (competing facts and effective-dated master data), and the partner gateway. | docs/source-systems-and-constraints.md |
| SourceContract | Declared shape of messages from a source (integration/source-contract-v1.json). | integration/source-contract-v1.json |
| FeedItem | One message received from a source, kept exactly as received. | docs/12-specs/business-rules.md |
| IntakeOutcome | The deterministic classification of a FeedItem: outcome, primary reason (by fixed precedence), all reasons, queue, contract check and whether it counts toward totals. | hub/intake/reasons.py |
| Document | An immutable (doc_id, version) extracted/archived document: SOP, certificate of analysis (COA) or batch record, with locale, source, effective date, access level and OCR confidence. | docs/11-data-context/knowledge-model.md |
| CrosswalkLink | An explicit, exact-key link between two objects of different identifier spaces (case, batch, deviation, CAPA, lab result, feed item, document). | hub/crosswalk/registry.json |
| PolicyException | A legacy record that a policy was waived, blocked or put under review for a referenced object. | docs/partner-feed-operations.md |
| UpstreamOutage | A recorded outage or partial rerun of an upstream system, with began/resolved times; some are unresolved. | docs/04-baseline-kpis/kpi-dictionary.md |
| MetricDefinition | A declared measure: category, window, denominator, exclusions, basis and — where closed/resolved/approved/cost/handling is involved — a mandatory definition tag. | hub/metrics/registry.py |
| MetricValue | One computed figure with its window, denominator, exclusions, definition tag, policy version, data origin and the label 'synthetic, unvalidated' while data are synthetic. | docs/12-specs/contracts/ddl/hub-schema-v0.1.sql |
| OperatingCost | Monthly modelled operating-cost estimate (labour hours, cases, infrastructure USD). | .fde/orchestrator-decisions.md |
| Run | One execution of a closed-catalogue job (intake, backfill, rebuild/verify projection, verify audit, metrics snapshot), recorded as append-only run events including inputs seen, outcomes, errors and remaining backlog. | hub/runs/catalogue.py |
| Principal | An authenticated actor: a human with one or more roles, a service account (token prefix svc_, role integration, never Zone H), or a system/rule actor. | hub/security/authz.py |
| AuditRecord | Hash-chained access/audit entry written in the same transaction as the change it audits. | hub/security/audit.py |
| DeviationRegisterEntry | A recorded difference between legacy behaviour (golden baseline) and hub behaviour (DV-01..DV-11) with a preserve-or-fix decision. | docs/16-repo-validation/behavior-difference-report.md |
| Capability | One of ten product capabilities CAP-01..CAP-10. | docs/final-prd/final-capability-map.md |
| D-OPS | Definition tag: closed/resolved as operations sees it (status reached a closing state). | docs/04-baseline-kpis/kpi-dictionary.md |
| D-EVID | Definition tag: closed AND evidence complete AND authorised approver recorded. | docs/04-baseline-kpis/kpi-dictionary.md |
| D-FIN | Definition tag: 'successfully resolved for cost'. Undefined (OPD-01). | docs/04-baseline-kpis/kpi-dictionary.md |
| Zone H | The ten closed human-only actions ZH-01..ZH-10 that automation may never perform. | docs/12-specs/business-rules.md |
| Shadow mode | The hub runs beside the legacy code and never writes to legacy tables. | docs/final-prd/final-as-built-prd.md |
| Epistemic status | Label on every statement: verified_fact, inference, assumption or unknown. | semantic-layer/ai-context-policy.yaml |
| Natural key | Intake identity (partner, record_kind, ref_id, source_ts). | docs/12-specs/business-rules.md |
| Accepted open | A recorded statement that a decision is undecided; not a resolution. | docs/12-specs/business-rules.md |
| Synthetic | All data is generated (seed 4100); not production and not validated. | docs/04-baseline-kpis/kpi-dictionary.md |
| Fan-out | Join duplication inflating a total (legacy month-end 742,956.61 vs 622,826.44). | docs/06-root-cause/confirmed-root-causes.md |
