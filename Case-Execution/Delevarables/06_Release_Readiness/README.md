# 06 Release readiness: path from NO-GO to GO (shadow)

Prepared 25 Oct 2026. All data synthetic. Nothing here approves anything: the hub's release check refuses approvals not made by a named human.

## Where things stand (the repo's own evaluator, run on a clean copy of `main`)
- Technical criteria: **17 of 20 pass**. T-05 (full regression) is now green on **Python 3.14.6**: 31 of 31 groups, 586 of 586 tests executed as expected at main a2b4828, before Stage 44 (main e62c9b4: 33 groups, 613 executed, 1 skip, Python 3.13 cloud sandbox; Python 3.14 re-run pending) (one skip: python3.9 not installed). Blocking: **G1, T-09, T-10**.
- Approvals: **0 of 40**. 22 are needed for GO (shadow), including AP-GATE-G1..G10 and AP-OPS-01..11.
- Result today: **NO-GO**.

## Files
| File | What it is |
|---|---|
| `Release_Decision_Workbook.xlsx` | Your sign-off sheet: 40 approvals, 11 differences to decide, 4 security decisions, monitoring choice, path to GO. Yellow cells are yours. |
| `T-10_Security_Decisions_Draft.md` | Facts and options for VR-02, VR-03, VR-04, F-11. Draft, not a decision. |
| `T-09_Monitoring_Acceptance_Draft.md` | Draft wording to accept manual monitoring for the shadow window. |
| `tools/release_check.py` | `validate` (reads your workbook) and `evaluate` (runs the repo's own go/no-go on a sandbox copy). Never writes to your repository. |
| `evidence/regression-py314-main.json` | Full regression log, clean `main` a2b4828, Python 3.14.6. |
| `evidence/regression-py314-branch-docs-readme-hub-ui.json` | Same run on your current branch: 4 tests fail (see below). |

## Your steps (about 60 to 75 minutes)
1. Open the workbook. Type your name and date on `Start here`. Read the evidence in each row, then choose APPROVED / REJECTED / OPEN. Fill the Security and Monitoring sheets.
2. `py -m pip install openpyxl` (once).
3. `py -3.14 tools\release_check.py validate --workbook Release_Decision_Workbook.xlsx`
4. `py -3.14 tools\release_check.py evaluate --workbook Release_Decision_Workbook.xlsx --regression-log evidence\regression-py314-main.json`
   It finds the repo and the backup next to the `Delevarables` folder (or pass `--repo` and `--backup`). The repo's evaluator prints GO or NO-GO. Use the repo's HEAD you intend to release; on branch `docs/readme-hub-ui` see note 2 below.
5. Only then copy the signed workbook and the generated files into `docs/30-release/` in the repo and commit as your decision. The deck stays at NO-GO until that evaluator prints GO.

## Three things to know before you start
- **Your working folder differs from the baseline.** `data/legacy.sqlite3` no longer matches the Stage 0A backup checksum (2855e3c1... instead of c254649f...), so the repo's own test runner refuses to start in your folder (STOP-01). The sandbox runs used the backup copy. Find out what changed the file; I could not tell from here.
- **The README change trips a guard.** On branch `docs/readme-hub-ui`, TST-CO-05 and TST-CO-12 shard 3 fail because `README.md` is modified (a legacy path) and `scripts/hub_ui_demo.sh` is untracked. On `main` everything passes. Decide how the README change is carried before using that branch as the release HEAD.
- **DV-08.** The repo recommends not cutting over the night-shift figure, yet G1 needs every difference approved. See the note on the `Differences (11)` sheet.

**Stage 44 note.** Update 26 Oct 2026 (Stage 44, merged as PR #32, main e62c9b4): the hub itself now has an optional, off-by-default advisory document Q&A that can use Azure OpenAI (decision OD-40 in the repo). It is separate from the Command Centre assistant (decision OD-41, which the repo log did not previously hold). It is disabled in the shipped configuration and needs an approval reference to enable. It answers only from hub search results with citations and uses synthetic data only. It was tested only against a local fake Azure server; no real Azure call was made, so it is not proven against a live deployment. The core decision path is still No-AI. Details: docs/44-genai-qa/ in the repo. The 40 approvals are unchanged; enabling the Q&A needs its own approval reference for ai.enabled.
