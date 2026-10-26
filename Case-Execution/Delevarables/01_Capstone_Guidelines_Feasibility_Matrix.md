# AI FDE Capstone — Feasibility Check of the 28 Guidelines

**Prepared:** 2026-10-25 · **Repo assessed:** `gxp-quality-hub-legacy` (main `a2b4828`, Stage 43 merged) · **Source of the guidelines:** `AI_FDE_Capstone_—Final_Presentation_Guidelines.pdf`

**Scope you gave me:** go through each point, say whether the required artifact can be created, and treat the Stage 42 (Executive Defence) deliverable as already done.
This document only *checks* feasibility. It does not build the apps, deck or demo. The one thing built now is the **semantic layer** (see `semantic-layer/`).

---

## 1. Read this first — five findings that change the plan

| # | Finding | Why it matters | Evidence |
|---|---|---|---|
| F-1 | **The product is formally No-AI.** You answered "Accept No-AI" (OD-08, 2026-10-18); FR-CO-04 / PNFR-18 forbid any LLM/ML call; Stages 19 (Intelligence) and 22 (Agentic) are NOT APPLICABLE. Update 26 Oct: Stage 44 (OD-40) re-qualifies T3 only: an optional, off-by-default advisory Azure OpenAI document Q&A now exists in the hub. | Guidelines #6 (agentic AI), #7 (knowledge graphs), #17 (AI intelligence in demo), #24 (GenAI justification) cannot be met "as written" by the current build. They need either (a) an honest "GenAI deliberately not used, here is why" story, or (b) a new decision to re-qualify AI (triggers RQ-1..RQ-3). **Updated 25 Oct: you chose to add an advisory OpenAI assistant (autonomy A1) on top of the deterministic core; recorded as OD-41 in the semantic layer.** | `.fde/orchestrator-decisions.md` OD-08; `docs/08-ai-qualification/qualification-decision.md` QD-1, QD-3 |
| F-2 | **"Two functional applications" is not yet satisfied.** One app exists: the shadow `hub/`. The second ("Context-Lake ported application") is the app regenerated *from the semantic layer with a different model* (challenge guide: Develop APP → Test semantic layer with new model → Compare both). | Needs to be built later. The semantic layer captured now is its input. | `semantic-layer-build.txt`; challenge guide p.6 |
| F-3 | **Release is BLOCKED and value is not computable.** 0 of 40 approvals, evaluator says NO-GO, ROI/NPV/payback "NOT COMPUTABLE", no after-window. | Guidelines #14, #21, #23 ask for measured improvement. Only parity and mechanism-level evidence exists. I will not invent numbers; the deck must say so (the repo's own pitch rules forbid "saves X %", "production-ready", "AI-powered"). | `docs/final-prd/final-as-built-prd.md`; `docs/42-executive-defence/elevator-pitch.md` EP-4 |
| F-4 | **Birlasoft branding assets are not in the folder (updated 25 Oct: styled from the annual-report sample you provided).** No logo, corporate `.potx` template or brand guideline found. | Guideline #15 (and the visual quality of #16/#25) is blocked until you provide approved assets. | folder listing |
| F-5 | **UI is thin** (updated 25 Oct: the Command Centre adds 9 views over the hub). 7 server-rendered screens/actions, loopback only, standard library only (no TLS). | Guideline #5 asks for dashboards, navigation, role-based experiences. Gap is real; closing it is new build work and may conflict with the stdlib-only/loopback ADRs. | `hub/web/ui_routes.json`; ADR-014, ADR-015 |

---

## 2. Legend

| Verdict | Meaning |
|---|---|
| **YES** | Evidence exists in the repo; I can create the artifact now from it. |
| **PARTIAL** | I can create most of it, with a stated gap or an honest limitation. |
| **BLOCKED** | Needs something only you can provide (asset, decision), or conflicts with a recorded decision. |
| **LATER** | Needs a build step that has not been done (e.g. the second app). |

---

## 3. Section A — Capstone Engineering & Transformation (#1–#18)

| # | Guideline | Verdict | What I can create | What the repo already gives me | Gap / limitation | Needs from you |
|---|---|---|---|---|---|---|
| 1 | 42-Stage AI FDE Spine | **YES** | *Spine coverage & adaptation log*: one row per stage (00A–43) with status, depth, what was adapted | 46 stage prompts executed 0A→43; statuses in git log + OD-01..OD-39. N/A: 19, 22. BLOCKED: 30, 38, 41, 43. Most others CONDITIONAL PASS | Statuses are the agent's own; no external review | none |
| 2 | Prompt Adaptability | **YES** | *Prompt adaptation register*: what was added, combined, skipped or changed and why | Added pre-flight 0A/0B/0C; Stage 19/22 skipped by decision; path deviations (S28-DEV-05 `28-reliability` vs `28-resilience`, S43-DEV-01 `final-prd`); "test once" and parallel doc stages (OD-23). The two prompt copies (`FDE_Stage_System_Prompts` and `.fde/stage-prompts`) are byte-identical, so no prompt *text* was edited | Adaptations were made in execution, not by editing prompts (LL-16 says fix paths at source) | Confirm if you edited any prompt elsewhere |
| 3 | Enterprise Context Lake | **PARTIAL** | *Context-Lake manifest*: versioned index of every context asset (978 doc files, ADR-001..018, OD log, specs, schemas, evidence logs, semantic layer) with type, stage, hash and evidence tier [Verified Fact/Inference/Assumption/Unknown] | Evidence-tagged docs, SHA256SUMS files, traceability matrix (docs/13), package graph, semantic layer (new) | No queryable store; "code intelligence" is a text package graph, not an index. **Naming clash:** `data/lake/` in the repo is synthetic event data, *not* the Context Lake | Confirm the Context Lake may be a file-based manifest + semantic layer rather than a database |
| 4 | Two functional applications | **PARTIAL** (updated 25 Oct) | App A = legacy estate; App B = shadow hub + **GxP Quality Command Centre** (`04_Quality_Command_Centre/`) with an advisory OpenAI assistant | Legacy app, hub (204 py files, 17,247 lines), Command Centre (9 views) reusing the hub's intake, metrics and crosswalk code | The 'regenerated from the semantic layer on a second model' portability run has not been done | Access to a second model if the portability comparison is wanted |
| 5 | Enterprise-grade UI/UX | **YES** (updated 25 Oct) | Running Command Centre: executive overview, cases with trace drawer, intake & exception queues, month-end truth, definitions, Zone H gate, AI assistant, release evidence, system; 6 role personas, deny-by-default | Hub's 7 server-rendered screens remain the system of record for actions | Read-only (no reviewer writes in the new UI); personas are demo personas, not authentication; loopback only | none |
| 6 | Agentic AI engineering | **PARTIAL** (updated 25 Oct) | Advisory assistant (autonomy A1) with guard → retrieve → wrap → generate → label/log pipeline; Zone H refusals for AI actors; autonomy ladder A0–A5 | You chose to add an OpenAI assistant (25 Oct). Core decision path stays deterministic (OD-08). Multi-step planning agents (A4) are not built | No multi-step agent or tool orchestration; assistant not evaluated on real documents (RQ-1) | Decide whether an A2 'draft evidence pack for human approval' agent is in scope |
| 7 | Knowledge graphs | **PARTIAL** | *Graph export* from the semantic layer: nodes/edges JSON + Mermaid diagram; optional RDF/Turtle | `relationships.yaml` (new), crosswalk (7 id types, 6 link-type codes / 8 type pairs, 168 exact-key links), joined view | Stage 11 chose *no* graph database; enterprise graph has one untyped relation (`relates_to`, ER-11-02). "Justified by use case" is arguable for explainability only | none (I can proceed with the lightweight export) |
| 8 | Semantic Layer | **YES — done now** | Delivered: `semantic-layer/` (glossary, entities, relationships, status taxonomy, business rules, metrics, access semantics, AI-context policy, workflows, constraints, context dependencies, JSON schema, generated JSON, tests, assessment) | See §6 | Not yet proven portable — requires the model-swap test | Run the portability test when ready |
| 9 | Specification-Driven Development | **YES** | *SDD evidence index*: requirement → spec → contract → ADR → acceptance criterion | 52 FRs + 20 PNFRs, 48 spec business rules (SBR), 10 feature specs, OpenAPI (48 ops), 16 JSON schemas, DDL, AC-* criteria, 18 ADRs (all still DRAFT status) | ADRs never individually ACCEPTED (AB-AR-7) | none |
| 10 | Test-Driven Development | **YES** | *Test pyramid & evidence summary* (characterization, unit, integration, regression, contract, e2e, mutation) | Characterization harness 134/134; mutation gate 15/15 (vs shipped suite 1/15); 396 ok / 1 skipped at Stage 16; 419 methods at Stage 20, 31 regression groups green at final merge; planned tests per increment written before build | CT-13 fails on Node patch drift; test totals not re-run at final HEAD (U-43-12); no CI installed | Permission to re-run in a sandbox copy if you want fresh numbers |
| 11 | Security & Threat Modeling | **YES** | *Security story*: threat model, attack surface, control matrix, red-team results | `docs/24-security-privacy/*`, TEVV (11 findings, no Critical, 1 High fixed under assumption), Stage 27 hardening (F-01..F-07 fixed) | No LLM/RAG/agent threats because there is no AI; no TLS, no 2FA, no external pen test | none |
| 12 | Compliance & Governance | **YES** (with wording limits) | *Compliance & governance summary*: obligations OB-01..OB-16, control matrix, system card, model card, AI-system register | `docs/25-governance/*` | You decided "Part 11 *framing* only, no 'compliant' claims" (OD-30). Retention is hold-all; privacy regime not assessed | none |
| 13 | Production Engineering | **PARTIAL** | *Built-vs-wired readiness matrix* (observability, resilience, rollback, performance, scalability, ops readiness) | Stages 27–31: runbook, SLO candidates (5), failure injection, backup/restore + rollback rehearsal, RTO/RPO targets | Resilience, observability exports, release evaluator, CI file exist but are **not wired/installed**; no deployed environment; 24 of 38 readiness checks met | Decide whether to wire them before the demo |
| 14 | Evidence-Based Comparison | **PARTIAL / LATER** | *Comparison harness design* + scenario set; legacy-vs-hub table from Stage 34/35 | Identical scenarios exist (FX-BASE125, goldens). Only 3 like-for-like KPI pairs, all "sandbox parity" | Needs App B for A-vs-B. ROI not computable; latency has no target; model cost is USD 0 by design. No improvement can be claimed | App B (see #4) |
| 15 | Birlasoft Branding | **PARTIAL** (updated 25 Oct) | Deck, Command Centre and diagrams styled from the Birlasoft Annual Report 2024-25 sample (wordmark, red/grey palette, two-line grey + red headings) | `Requried-External-Input/sample-Birlasoft-PPTx.pdf` | No official .potx template or brand guideline; fonts substituted with Arial (the report uses Locator) | Official template if one exists |
| 16 | Board-Level Presentation | **YES** (updated 25 Oct) | `05_CTO_Presentation/GxP_Quality_Hub_CTO_Presentation.pptx`: 31 slides with speaker notes (Team Delta on the title slide; before/now architecture, hub module map and engineering comparison slides), CTO audience, 3W + How, problem → solution → functional flow → technical implementation → evidence → value → lessons → moonshots | Stage 42 content, Command Centre screenshots, input brief `Input-for-PresentationsDeck.txt` | Value slides state 'not computable' where true | Rehearse timing (about 1.5 min per slide) |
| 17 | Live End-to-End Demonstration | **YES** (updated 25 Oct) | Command Centre live demo on the local machine with **Python 3.14** (`start-windows.bat` or `py -3.14 run.py`); 8-minute demo path in its README; deck slides 18–21 are the recorded fallback | Tested on Python 3.14.6 and 3.10.12; 15 app tests pass; reproduces 89/125, 742,956.61 vs 622,826.44, 8,335 queue items, replay Δ 0 | The hub's own test suite has not been re-run on 3.14 (goldens were recorded on 3.10, LL-18) | Optional: set OPENAI_API_KEY to show model mode |
| 18 | Engineering Evidence & Traceability | **YES** | *Evidence index*: claim → artifact → test/log → hash | Claims register C-01..C-34, RTM (docs/13), SHA256SUMS per stage, golden manifests | Human sign-offs are all open | none |

---

## 4. Section B — Final Presentation & Executive Defence (#19–#28)

| # | Guideline | Verdict | What I can create | Already in repo (Stage 42 and earlier) | Gap / limitation | Needs from you |
|---|---|---|---|---|---|---|
| 19 | Time-boxed (40 + 10 min) | **YES** | Minute-by-minute run-of-show with demo cut-points and Q&A bank | `demo-day-script.md` (15–20 min) to extend to 40 | Needs the second app for a full 40 min | Confirm demo order |
| 20 | Compelling storytelling | **YES** (honest framing) | Narrative arc: problem → consequences → journey → outcomes | `executive-narrative.md`, `problem-to-value-story.md`. Data hooks: month-end total 742,956.61 vs 622,826.44 (19.3 % join fan-out); 97.98 % of feed rows unmatched | Consequences are not quantified in money; no real stakeholders | none |
| 21 | Problem → Solution → Impact | **PARTIAL** | One-page P→S→I | Eight confirmed root causes RC-1..RC-8; solution = 10 capabilities; impact = parity + risk-control mechanisms | "Business value delivered" is not measurable today | none |
| 22 | Business + technical balance | **YES** | Slide-budget plan (equal weight) | Business: personas, KPIs, value hypothesis. Technical: ADRs, specs, tests | — | none |
| 23 | Before vs After KPIs | **PARTIAL** | KPI before/after charts for 22 KPIs, colour-coded by comparability class | Stage 34 sheet. Comparable: backlog 89/125 (parity), reopen rate 6.4 % (parity), replay safety Δ0, decisions recorded 0→2 of 2 | Most KPIs Unknown (no closure/evidence timestamps). K-03 0 %→4/4 is *not* like-for-like. Productivity/performance have no baseline | Decide whether to add measured build-effort data |
| 24 | GenAI Value Justification | **PARTIAL** (updated 25 Oct) | Deck slides 'Which gains came from AI' and 'What AI can and cannot do'; assistant demonstrates grounded explanation with citations | `ai-decision-defence.md`; Command Centre assistant; semantic layer as model-portable context | Every measured improvement came from traditional engineering; AI value (reviewer time, answer quality) is not yet measured; build-effort saving not recorded (LL-14) | A labelled question set (RQ-1) to evaluate the assistant |
| 25 | Visual-first communication | **YES** | Architecture, workflow, graph, KPI and traceability diagrams | Component model, ADRs, workflows, semantic layer | Branding (#15) | Branding assets |
| 26 | Evidence-based demonstration | **YES** | Proof-of-work bundle: logs, test outputs, hashes | `s30-log-*`, `docs/16-repo-validation/evidence`, TEVV evidence, golden compare | Fresh run optional | none |
| 27 | End-to-end transformation traceability | **PARTIAL** | Traceability ribbon: discovery (S5/7) → rule extraction (S6/12) → architecture (S10) → modernization (S15) → validation (S16/26) → readiness (S30) → semantic layer | All stages documented | "AI integration" step is N/A; production readiness = BLOCKED | none |
| 28 | Crisp lessons learned (4–5) | **YES** | Five lessons distilled from the 18 recorded (engineering, business, GenAI limits, unexpected, future) | `lessons-learned.md` LL-01..LL-18 | Lessons about *GenAI limits* come from the build process, not product use | none |

**Tally (all 28, updated 25 Oct 2026):** YES 17 (#1, 2, 5, 8, 9, 10, 11, 12, 16, 17, 18, 19, 20, 22, 25, 26, 28) · PARTIAL 11 (#3, 4, 6, 7, 13, 14, 15, 21, 23, 24, 27) · BLOCKED 0 · LATER 0. Previous tally (first check): YES 14 · PARTIAL 10 · BLOCKED 3 · LATER 1.

---

## 5. What I need from you (ordered by impact)

1. ~~AI stance~~ **Decided 25 Oct:** add an advisory OpenAI assistant (A1) on the deterministic core. Remaining: a labelled question set to evaluate it (RQ-1, #24).
2. ~~Brand assets~~ **Partly met 25 Oct:** styled from the annual-report sample. Remaining: an official template, if one exists (#15).
3. **Portability run (#4, #14):** access to a second model to regenerate the PRD/app from the semantic layer and compare.
4. **Wire the built-but-unwired controls?** (#13)
5. **Pilot window / after-window** for measured before-vs-after (#21, #23, #14).
6. ~~Demo machine~~ **Decided 25 Oct:** local machine, Python 3.14.

## 6. What was delivered

- 25 Oct update: `04_Quality_Command_Centre/` (running UI + OpenAI assistant, Python 3.14), `05_CTO_Presentation/` (31-slide deck), demo machine = local machine, Python 3.14.

- `semantic-layer/` — the captured semantic layer (no app built, as you asked).
- This matrix.
- `00_INDEX.md` — map of everything in this folder.

## 7. Release readiness update (25 Oct 2026, evening)
Guideline verdicts are unchanged (YES 17, PARTIAL 11). What changed under #14, #21 and #23 (release status and measured improvement):
- T-05 now has evidence: the hub's full regression ran on Python 3.14.6 in a sandbox copy of `main`: 31 of 31 groups, 586 of 586 tests executed as expected at main a2b4828, before Stage 44 (main e62c9b4: 33 groups, 613 executed, 1 skip, Python 3.13 cloud sandbox; Python 3.14 re-run pending) (`06_Release_Readiness/evidence/`). It is not yet recorded in the repo's `gate-results.json`.
- The repo's evaluator, fed that result, shows 17 of 20 technical criteria passing; **G1, T-09 and T-10 block**, approvals 0 of 40. Release stays **NO-GO**.
- The sign-off workbook, T-09 / T-10 drafts and `release_check.py` are in `06_Release_Readiness/`. A throwaway dry run showed G1 flips to pass once all 11 deviations are approved. Only you can approve; the hub refuses any other approver.
- Two repo-state findings: your working-folder `data/legacy.sqlite3` no longer matches the Stage 0A backup checksum (the repo's own test runner refuses to run there), and on branch `docs/readme-hub-ui` the README change fails TST-CO-05 / TST-CO-12 shard 3 (passes on `main`).

**Stage 44 note.** Update 26 Oct 2026 (Stage 44, merged as PR #32, main e62c9b4): the hub itself now has an optional, off-by-default advisory document Q&A that can use Azure OpenAI (decision OD-40 in the repo). It is separate from the Command Centre assistant (decision OD-41, which the repo log did not previously hold). It is disabled in the shipped configuration and needs an approval reference to enable. It answers only from hub search results with citations and uses synthetic data only. It was tested only against a local fake Azure server; no real Azure call was made, so it is not proven against a live deployment. The core decision path is still No-AI. Details: docs/44-genai-qa/ in the repo.
