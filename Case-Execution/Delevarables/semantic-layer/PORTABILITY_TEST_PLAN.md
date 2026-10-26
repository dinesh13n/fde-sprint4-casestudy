# Portability test plan (from semantic-layer-build.txt)

Goal: show a different model, given only `semantic-layer/` and no repo access, can regenerate a PRD and a matching app.

## Steps
1. Copy `semantic-layer/` (not the repo) into an empty folder. Run the unit tests; repo-backed ones skip.
2. Give a new model only: README.md, glossary.md, the YAML files and generated/semantic-layer.json.
3. Prompt A: "Write the PRD for this product." Prompt B: "Build the app as described." Forbid inventing values; unknowns must stay open.
4. Save outputs under `portability-run-<model>/`.
5. Compare against the original PRD (`docs/final-prd/`) and app using the template below.

## Compare template
| Dimension | Score 1-5 | Evidence / differences |
|---|---|---|
| PRD reproducibility (sections, rules, open decisions kept open) | | |
| App match (entities, routes, roles, Zone H refusals) | | |
| Context completeness (questions the model had to guess) | | |
| Model independence (same result across 2 models) | | |
| Repo dependency (facts the model could not get without the repo) | | |
| Knowledge-transfer quality (can a new engineer follow it) | | |

## Fail conditions
- The model resolves any open decision, names a Zone H holder, or invents a latency/ROI target.
- The model maps statuses across vocabularies.
- Any number appears that is not in the layer.
