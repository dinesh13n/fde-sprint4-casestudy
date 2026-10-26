"""Recorded engineering and release evidence, quoted from the repository documents (not recomputed by this app).
Each entry names its source so a reviewer can open the file. Numbers are synthetic / sandbox results.
"""
AS_OF = "2025-12-19T07:11:00+00:00"

RELEASE = {
    "verdict": "NO-GO",
    "status": "BLOCKED",
    "approvals": {"recorded": 0, "required": 40},
    "criteria": [
        {"id": "Technical criteria", "result": "16 pass", "state": "pass"},
        {"id": "G1 human approvals", "result": "fail (0 of 40)", "state": "fail"},
        {"id": "T-09 monitoring (persisted metrics, alerts)", "result": "fail", "state": "fail"},
        {"id": "T-10 High-finding dispositions recorded", "result": "fail", "state": "fail"},
        {"id": "T-05", "result": "not run", "state": "na"},
    ],
    "source": "docs/30-release/go-no-go-criteria.md; docs/30-release/release-approvals.md",
}

ENGINEERING = [
    {"label": "Legacy characterisation checks", "value": "134 / 134", "note": "behaviour preserved where checked", "source": "docs/16-repo-validation/regression-results.md"},
    {"label": "Mutation gate", "value": "15 / 15 killed", "note": "shipped legacy suite kills 1 / 15", "source": "docs/16-repo-validation/"},
    {"label": "Acceptance tests (sandbox)", "value": "241 green", "note": "hub acceptance criteria", "source": "docs/42-executive-defence/executive-narrative.md"},
    {"label": "TEVV findings", "value": "11 (0 Critical, 1 High)", "note": "Stage 27 fixed F-01..F-07", "source": "docs/26-tevv/red-team-findings.md"},
    {"label": "Rollback levels rehearsed", "value": "L1-L3", "note": "on sandbox copies", "source": "docs/30-release/"},
    {"label": "Readiness checks met", "value": "24 / 38", "note": "built-but-unwired controls remain", "source": "docs/final-prd/final-as-built-prd.md"},
    {"label": "Accepted asset owners", "value": "0 / 28", "note": "17 of 24 accountable roles vacant", "source": "docs/37-operating-model/raci.md"},
    {"label": "ROI / NPV / payback", "value": "Not computable", "note": "no after-window, no volumes, no rate", "source": "docs/36-roi/roi-model.md"},
]

ROOT_CAUSES = [
    ("RC-1", "No recorded decision step", "Append-only decision events with actor and basis; Zone H gate"),
    ("RC-2", "Mutable case state", "Append-only events and rebuildable projections"),
    ("RC-3", "No owned definition of 'closed'", "Definition tags D-OPS / D-EVID / D-FIN; candidate policies"),
    ("RC-4", "Three unsynchronised approval rules", "Single rule service; as-found rule sets loaded inactive"),
    ("RC-5", "Manual, unrecorded execution", "Idempotent runs with run records; scheduler OFF"),
    ("RC-6", "Destructive intake", "Raw store, content-hash idempotency, quarantine"),
    ("RC-7", "No shared identity model", "Explicit crosswalk, exact-key matching"),
    ("RC-8", "No shared month-end definition", "One metrics query path, exact decimals"),
]
ROOT_CAUSE_SOURCE = "docs/06-root-cause/confirmed-root-causes.md; docs/42-executive-defence/problem-to-value-story.md"
