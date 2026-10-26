# Deliverables index (updated 25 Oct 2026)

| Folder / file | Purpose | Guidelines |
|---|---|---|
| 01_Capstone_Guidelines_Feasibility_Matrix.md | All 28 guidelines checked. Now: YES 17, PARTIAL 11, BLOCKED 0, LATER 0 | all |
| 02_Excel_Tracker/Capstone_28_Point_Tracker_v2.xlsx | Current tracker: 28 guidelines with closure path, decisions, KPI before/after, lessons, hard Q&A, run of show (`Capstone_28_Point_Tracker.xlsx` is the first version) | all |
| 03_Word_Documents/Capstone_Readiness_Report.docx | Readiness report for the 28 points | all |
| 03_Word_Documents/Executive_Defence_Briefing.docx | Story, problem to solution to impact, GenAI justification, KPIs, five lessons | 16, 19-24, 27, 28 |
| 03_Word_Documents/Demo_and_Presentation_Plan.docx | 40+10 run of show, demo steps, pre-flight for the local machine (Python 3.14) | 16, 17, 19, 26 |
| 04_Quality_Command_Centre/ | Running UI over the built hub + advisory OpenAI / Azure OpenAI assistant (all AI parameters in `config/settings.json`). Start: `start-windows.bat` or `py -3.14 run.py` | 4, 5, 6, 17, 24, 25, 26 |
| 05_CTO_Presentation/GxP_Quality_Hub_CTO_Presentation.pptx | 31-slide CTO deck in the Birlasoft style, with speaker notes | 15, 16, 19-28 |
| 06_Release_Readiness/ | Path from NO-GO to GO (shadow): sign-off workbook (40 approvals, 11 differences, 4 security decisions, monitoring choice), T-09 / T-10 drafts, `release_check.py`, Python 3.14 regression evidence (31/31 groups, 586/586 tests on main) | 14, 21, 23 |
| 07_Stage_Evidence/Stage_Evidence_Before_After_46_Prompts.xlsx | Central evidence workbook: before vs after for all 46 stage prompts (0A, 0B, 0C, 1-42, FINAL), verdicts, repo before/after, behaviour before/after, 960-file evidence index with hashes, commit map | 3, 4, 15, 16, 19-23 |
| 08_Presentation_Guide/Presentation_Preparation_Guide_Problem_to_Build.docx | Plain-words self-study guide: problem, root causes, proposed solution, final build (business to technical), proof numbers, talk track, 14 hard questions, glossary, checklist (19 pages) | 15-28 |
| 09_Ontology/ontology_explorer.html (+ gxp-ontology.ttl, gxp-instances.ttl, sparql_results.md, README.md) | Demo ontology (OWL 2 + SKOS) generated from the semantic layer: 34 classes, 36 relationships, 56 vocabularies, metrics, rules, Zone H; offline explorer and 11 SPARQL queries; synthetic data | 15-28 |
| semantic-layer/ | Captured semantic layer with tests; OD-40 (advisory assistant) recorded in `ai-context-policy.yaml` | 8 |

All data is synthetic. The Stage 42 system prompt was already done and is not included.
Decisions recorded 25 Oct: advisory OpenAI assistant at autonomy A1 (OD-40); demo on the local machine with Python 3.14; branding from the annual-report sample.
Release status 25 Oct evening: repo evaluator NO-GO. 17 of 20 technical criteria pass (T-05 now green on Python 3.14 in a sandbox); G1, T-09, T-10 and 40 approvals wait for your decisions (see 06_Release_Readiness/README.md).
Still open: assistant evaluation set (RQ-1), second-model portability run, wiring of unwired controls, pilot / after-window, official template.
