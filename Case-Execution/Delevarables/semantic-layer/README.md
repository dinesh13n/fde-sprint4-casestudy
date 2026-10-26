# Semantic layer — GxP Quality Hub (legacy repo)

Captured from `gxp-quality-hub-legacy`. All data is **synthetic and unvalidated** (seed 4100). The hub is a shadow-mode, No-AI modular monolith; release is BLOCKED.

Rule of the layer: `.md` explains, `.yaml` defines, JSON Schema validates, tests protect, generated JSON serves.

| File | What it holds |
|---|---|
| glossary.md | Terms (every entity has one) |
| entities.yaml | 34 entities, identity, attributes, vocabulary, sensitivity |
| relationships.yaml | REL-01..36, crosswalk link types, known gaps |
| status-taxonomy.yaml | 56 `vocab.*` vocabularies; cross-vocabulary mapping forbidden |
| business-rules.yaml | Curated rules (BR, DS, LEG, VAL, INV, GOV) |
| spec-business-rules.yaml | 48 SBR rules (generated) |
| metrics.yaml | K-01..K-22, built-in metrics, SLO candidates, invariants |
| workflow-semantics.yaml | Legacy flow, intake, decisions, Zone H, policy, runs, release |
| domain-constraints.yaml | Machine-checkable invariants |
| access-semantics.yaml / access-permission-matrix.yaml | Roles, Zone H, classification; 48-route matrix (generated) |
| ai-context-policy.yaml | No-AI decision, untrusted text, forbidden inferences |
| context-dependencies.yaml | Open decisions OPD / OD-S12 / RQ and unknowns |
| error-catalogue.yaml | Error codes (generated) |
| schemas/, generated/, tests/, tools/ | Validation, serving JSON, tests, extractors |

## Rebuild and test
```
python3 tools/extract_from_repo.py [REPO_ROOT]   # regenerates the 3 generated YAML files
python3 tools/build_json.py                      # regenerates generated/semantic-layer.json
python3 -m unittest discover -s tests -v         # needs pyyaml, jsonschema
```
Repo root defaults to `../../../gxp-quality-hub-legacy`; override with `GXP_REPO`. Repo-backed tests skip if absent.
