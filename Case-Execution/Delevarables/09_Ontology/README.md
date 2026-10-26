# 09_Ontology: GxP Quality Hub ontology (demo)

**Synthetic, unvalidated.** Generated from the semantic layer of `gxp-quality-hub-legacy` (`../semantic-layer/*.yaml`). Nothing here is a validated GxP record, and no status has business meaning until a policy is adopted (Zone H ZH-05).

## Files
| File | What it is |
|---|---|
| `ontology_explorer.html` | Offline, single-file explorer (graph, classes, vocabularies, governance, metrics, rules, gaps, SPARQL). Open in a browser. **Use this for the demo.** |
| `gxp-ontology.ttl` | The ontology (OWL 2 + SKOS, Turtle): 34 classes, 36 object properties, data properties from attributes, 56 SKOS vocabularies (255 concepts), 40 metric definitions, 49 business rules, 6 roles, 10 Zone H actions, 7 workflows. |
| `gxp-instances.ttl` | Synthetic instance data from the baseline snapshot (125 cases, 125 batches, 125 lab results, 42 deviations, 21 CAPAs, 30 materials, 72 outages). |
| `sparql_results.md` | 11 demo queries with their results (run with rdflib). |
| `ontology.json` | Compact model feeding the explorer. |
| `tools/` | `build_ontology.py`, `run_sparql_demo.py`, `build_explorer.py`: regenerate everything. |

## Regenerate
```
pip install rdflib pyyaml
python tools/build_ontology.py --db <path>/legacy.sqlite3     # omit --db for schema only
python tools/run_sparql_demo.py
python tools/build_explorer.py
```

## Design decisions (what to say if asked)
- **Derived, not invented.** Every class, property, vocabulary, metric and rule comes from the YAMLs; each keeps its `epistemicStatus` and `evidence`.
- **Statuses are SKOS concepts, not an enum.** CLOSED appears in several vocabularies. No `skos:exactMatch` / `owl:sameAs` is asserted between them (SPARQL Q6, Q7).
- **Case links are absent on purpose.** Case to Batch/Deviation/CAPA links cannot be derived (GAP-REL-2); they are human decisions. Instance data therefore has none (SPARQL Q5 returns 0). Batch, LabResult, Deviation, CAPA and Material are linked through the four legacy foreign keys only.
- **Zone H holders = 0.** All ten human-only actions exist in the model; none has a named holder today.
- **Not included:** the enterprise database (12,500 untyped objects), the 8,567-row partner feed, and state/transition tables (the case-status default is "structural", not a strict table).
- **Demo scope.** Not a reasoner-checked model: no OWL reasoning or SHACL shapes were run; syntax and queries were verified with rdflib only.
