# T-10 — Security decisions: DRAFT for Dinesh Naik

**Status: DRAFT. Nothing here is a decision. Claude cannot record a decision for the Engagement lead.**
Prepared 2026-10-25. Label: synthetic, unvalidated. The product is No-AI (OD-08).

Criterion T-10 (docs/30-release/go-no-go-criteria.md): *every High vulnerability and every open High finding has a recorded decision by the Engagement lead.* The criterion needs a **recorded decision**, not a fix. Accepting a risk for a defined scope is a valid decision.

Choose in the workbook, sheet **Security (T-10)**, column G. This page gives the facts behind each choice.

## VR-02 — Python 3.10 is end of life
- **Fact (repo):** floor shipped at 3.10; 3.12 floor is selectable; CI file for 3.12/3.13 written but not installed (D-27-02, AP-OPS-07).
- **New evidence from this session:** the hub regression was run on Python 3.14.6 in a sandbox copy (result on the workbook's Technical sheet and in `06_Release_Readiness/regression-py314.json`). 3.12 itself was not run.
- **Option 1 — Accept for shadow.** Stay on 3.10 floor; shadow only, synthetic data, loopback, no exposure. Condition written into the decision: *before any exposure or real data, move to a supported interpreter (3.12+).*
- **Option 2 — Adopt the 3.12 floor now.** Needs a code/config change and a run on 3.12.
- **Claude's suggestion (not a decision):** Option 1 with the condition above.

## VR-03 — No TLS
- **Fact (repo):** the hub refuses any non-loopback bind through two independent checks (re-verified in Stage 23). Risk exists only if the hub is exposed.
- **Option 1 — Accept:** loopback-only; any exposure is a new decision with TLS.
- **Option 2 — Require TLS before release.**
- **Claude's suggestion:** Option 1.

## VR-04 — Legacy container files (root user, all-interface bind if started as shipped)
- **Fact (repo):** frozen legacy path (TST-CO-05 a). Findings and fix list in `docs/27-hardening/runtime-hardening.md` RH-4. Deferred to Stage 30 (D-27-06).
- **Option 1 — Accept:** leave the legacy files unchanged; do not start the legacy containers; hardened recipe stays a proposal (deployment-strategy DS-5).
- **Option 2 — Harden the legacy files now** (changes a frozen legacy path and needs the characterization suite re-run).
- **Claude's suggestion:** Option 1.

## F-11 — Red-team finding S26-F-11 (group wall times)
- **Fact (repo):** listed as **Low** in `docs/26-tevv/red-team-findings.md` (S26 145 s, E26 174 s against the 180 s per-call cap of the reference laptop). The criterion text calls it an "open High finding"; the findings table does not. **Please confirm it belongs in T-10.**
- **Evidence from this session:** the full regression ran in the cloud workspace with no per-call cap.
- **Option 1 — Accept / backlog.** **Option 2 — Split the two slow groups.**
- **Claude's suggestion:** Option 1.

## How the decision becomes a gate result
`release_check.py evaluate` reads your choices (and the reason for any OTHER), your name and the date from the workbook, and writes `T-10 = pass` into a **sandbox copy** of `gate-results.json`, citing the workbook as evidence. You then copy the signed workbook into `docs/30-release/decisions/` in the repository so the evidence reference is true.
