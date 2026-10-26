# Assessment: semantic completeness and portability

Status: **draft, self-assessed, untested by a second model.** Nothing here proves portability until PORTABILITY_TEST_PLAN.md is run.

## What the layer captures well
- Vocabulary and meaning: 34 entities, 56 vocabularies, glossary, with the "CLOSED means four things" trap made explicit.
- Rules: 48 spec rules (generated from the repo) plus curated business, legacy, validation, invariant and governance rules.
- Metrics: definition-tag splits (OPS/EVID/FIN), synthetic baselines, SLO candidates, and what is deliberately target-less.
- Access: 48-route default-deny matrix, six roles, Zone H with zero holders.
- Honesty: every open decision and unknown is catalogued so a generator cannot silently decide it.

## Gaps that stop an independent app being generated from the layer alone
1. **No data.** The seeded database (125 cases, feeds) is not in the layer; numbers are quoted, not reproducible without the repo (DEP-01).
2. **No UI semantics.** Seven screens exist in the repo; screen layout, copy and flows are not captured.
3. **API shapes.** Routes and roles are captured; request/response schemas (16 JSON schemas in the repo) are not.
4. **Algorithms.** Intake reason precedence, rule evaluation and hash-chain computation are described, not specified to byte level.
5. **Business rules not in the spec.** Some legacy behaviour (LEG-xx) is inferred from code; epistemic_status marks these.
6. **The two-app requirement** in the capstone guidelines is not defined anywhere (see feasibility matrix, F-2).
7. **Evidence paths** are checked by test against the repo, but not that the cited text supports the claim.

## Portability judgement (before testing)
| Dimension | Expected | Why |
|---|---|---|
| PRD reproducibility | Medium | Concepts, rules, open decisions captured; narrative and scope choices not |
| App match | Low | No schemas, UI or data |
| Context completeness | Medium-high | Context dependencies explicit |
| Model independence | High | Plain YAML/JSON, no model-specific content |
| Repo dependency | Medium | Evidence and baselines point into the repo |
| Knowledge-transfer quality | Medium-high | Glossary, README, explicit gaps |
