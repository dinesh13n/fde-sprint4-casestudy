# T-09 — Monitoring for the release window: DRAFT for Dinesh Naik

**Status: DRAFT. Nothing here is a decision.** Prepared 2026-10-25. Label: synthetic, unvalidated.

## What T-09 asks
*Monitoring coverage for the release window: persisted metrics, alert delivery and an owner.* Today: no persisted metrics (F-31-02, D-31-01), no alert delivery and no on-call (F-29-03, D-31-08). The criteria document says T-09 *"can be cleared by AP-OPS-05 plus the wiring decisions D-31-01/D-31-08, or by Dinesh explicitly accepting manual monitoring for the release window."*

## Option A — Accept manual monitoring (suggested for a shadow release)
Draft wording for the decision record:

> I, Dinesh Naik (Engagement lead), accept manual monitoring for the shadow-release window. I am the monitoring owner. I run the routine evaluation RB-00 (docs/31-observability/operational-runbook.md) at the start and end of each working session, read `alerts.firing`, then `alerts.no_data`, then `slo`, and write what I saw in the run notes. No alert delivery and no on-call exist; none is claimed. The window covers synthetic data, loopback only. Before any real data or exposure this decision is void and D-31-01 / D-31-08 are decided again.

Consistent entries on the Sign-offs sheet: **AP-OPS-05** = manual evaluation (RB-00) until a second human exists; **AP-OPS-10** = release without wiring.

What stays true: six metrics are not exported (audit_chain_verify_ok etc., F-31-04), so some alerts report `no_data`; RB-04 gives the manual equivalent (`verify-audit` on a sandbox copy).

## Option B — Wire persisted metrics (not needed for shadow)
Edit `hub/web/app.py` to flush HTTP counters on an interval and add a snapshot job (D-31-01); export the six gap metrics (D-31-06); new tests. Alert delivery and on-call would still not exist, so T-09 would still need an owner decision. Estimate: about 1 hour of Claude work plus your review. Requires AP-OPS-10 = "wire before release".

## Claude's suggestion (not a decision)
Option A. It is honest about what exists, needs no code change, and the criteria document allows it.
