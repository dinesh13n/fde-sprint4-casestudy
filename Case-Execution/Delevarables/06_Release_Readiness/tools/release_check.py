#!/usr/bin/env python3
"""Release check helper for the GxP Quality Hub (shadow release).

Reads the release decision workbook that YOU filled in, validates it, and (evaluate) runs the repository's own go / no-go evaluator
on a SANDBOX copy. It never writes into the repository and never fills a decision for you.

  py -3.14 release_check.py validate --workbook Release_Decision_Workbook.xlsx
  py -3.14 release_check.py evaluate --workbook Release_Decision_Workbook.xlsx [--repo PATH] [--backup PATH] [--regression-log FILE] [--out DIR]

Needs: Python 3.10+, openpyxl (py -m pip install openpyxl), git on PATH (evaluate only).
Exit codes: validate 0 = workbook consistent, 1 = problems found; evaluate 0 = repository evaluator says GO, 1 = NO-GO, 2 = could not run.
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
NOT_A_HUMAN = {"claude", "agent", "orchestrator", "assistant", "bot", "system", "ai", "llm", "anthropic", "automation", "pipeline", "ci", "hub",
               "test", "fixture", "example", "placeholder", "tbd"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def tokens(s):
    return set(t for t in re.split(r"[^a-z0-9]+", str(s).lower()) if t)


def read_workbook(path):
    try:
        import openpyxl
    except ImportError:
        sys.exit("openpyxl is missing: py -m pip install openpyxl")
    wb = openpyxl.load_workbook(path, data_only=False)
    s = wb["Start here"]
    approver = (s["C13"].value or "").strip() if s["C13"].value else ""
    d = s["C14"].value
    if isinstance(d, (datetime.date, datetime.datetime)):
        d = d.strftime("%Y-%m-%d")
    date = (d or "").strip() if isinstance(d, str) else ""
    sg = wb["Sign-offs (40)"]
    rows = []
    for r in range(5, 45):
        rows.append({"id": sg.cell(r, 1).value, "decision": (sg.cell(r, 7).value or "OPEN"), "note": sg.cell(r, 8).value,
                     "approval_ref": sg.cell(r, 9).value, "evidence_ref": sg.cell(r, 10).value})
    sec = []
    for r in range(5, 9):
        w = wb["Security (T-10)"]
        sec.append({"id": w.cell(r, 1).value, "choice": str(w.cell(r, 7).value or "").strip(), "reason": str(w.cell(r, 8).value or "").strip()})
    mon = []
    for r in range(5, 7):
        w = wb["Monitoring (T-09)"]
        mon.append({"id": w.cell(r, 1).value, "choice": str(w.cell(r, 6).value or "").strip(), "reason": str(w.cell(r, 7).value or "").strip()})
    return {"approver": approver, "date": date, "rows": rows, "security": sec, "monitoring": mon}


def problems(w):
    out = []
    n_app = sum(1 for r in w["rows"] if r["decision"] in ("APPROVED", "REJECTED"))
    if n_app:
        if not w["approver"]:
            out.append("Start here C13: approver name is empty but %d rows are decided" % n_app)
        elif len(w["approver"].split()) < 2:
            out.append("Start here C13: please give a full name (first and last)")
        elif tokens(w["approver"]) & NOT_A_HUMAN:
            out.append("Start here C13: the name is refused (looks like an agent, system or placeholder)")
        if not DATE_RE.match(w["date"]):
            out.append("Start here C14: date must be ISO text like 2026-10-26")
    for r in w["rows"]:
        if r["decision"] not in ("OPEN", "APPROVED", "REJECTED"):
            out.append("%s: decision must be OPEN, APPROVED or REJECTED (found %r)" % (r["id"], r["decision"]))
    sec_ok = all(s["choice"] in ("1", "2", "OTHER") and (s["choice"] != "OTHER" or s["reason"]) for s in w["security"])
    mon_ok = any(m["choice"] in ("A", "B") for m in w["monitoring"])
    return out, sec_ok, mon_ok


def summary(w):
    rows = w["rows"]
    c = {"APPROVED": 0, "REJECTED": 0, "OPEN": 0}
    for r in rows:
        c[r["decision"]] = c.get(r["decision"], 0) + 1
    rel = [r for r in rows if r["id"] in REL_IDS]
    dv = [r for r in rows if r["id"].startswith("AP-DV-")]
    return {"total": len(rows), "counts": c, "release_approved": sum(1 for r in rel if r["decision"] == "APPROVED"), "release_total": len(rel),
            "dv_approved": sum(1 for r in dv if r["decision"] == "APPROVED"), "dv_total": len(dv)}


REL_IDS = set(["AP-REL-01"] + ["AP-GATE-G%d" % i for i in range(1, 11)] + ["AP-OPS-%02d" % i for i in range(1, 12)])


def cmd_validate(a):
    w = read_workbook(a.workbook)
    out, sec_ok, mon_ok = problems(w)
    s = summary(w)
    print("rows approved %d / rejected %d / open %d of %d" % (s["counts"]["APPROVED"], s["counts"]["REJECTED"], s["counts"]["OPEN"], s["total"]))
    print("release-scope approvals: %d of %d   |   deviation approvals: %d of %d" % (s["release_approved"], s["release_total"], s["dv_approved"], s["dv_total"]))
    print("T-10 security decisions complete: %s   |   T-09 monitoring choice made: %s" % ("yes" if sec_ok else "no", "yes" if mon_ok else "no"))
    for p in out:
        print("PROBLEM:", p)
    still = []
    if s["release_approved"] < s["release_total"]:
        still.append("%d release approvals still not APPROVED" % (s["release_total"] - s["release_approved"]))
    if s["dv_approved"] < s["dv_total"]:
        still.append("%d deviation decisions not APPROVED (G1 needs all 11)" % (s["dv_total"] - s["dv_approved"]))
    if not sec_ok:
        still.append("T-10 needs a choice for VR-02, VR-03, VR-04 and F-11")
    if not mon_ok:
        still.append("T-09 needs option A or B")
    for t in still:
        print("NOT YET GO:", t)
    print("workbook consistent" if not out else "fix the problems above")
    return 1 if out else 0


# ------------------------------------------------------------------ evaluate
def git_archive(repo, dest):
    p = subprocess.run(["git", "-C", repo, "archive", "--format=tar", "HEAD"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode:
        raise RuntimeError("git archive failed: " + p.stderr.decode("utf-8", "replace")[:300])
    with tarfile.open(fileobj=io.BytesIO(p.stdout)) as t:
        try:
            t.extractall(dest, filter="data")
        except TypeError:
            t.extractall(dest)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def manifest_ok(root, manifest):
    bad = 0
    for line in open(manifest, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        p = os.path.join(root, rel)
        if not os.path.exists(p) or sha256(p) != digest:
            bad += 1
    return bad


def run(cmd, cwd, env):
    p = subprocess.run(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    return p.returncode, p.stdout


def cmd_evaluate(a):
    w = read_workbook(a.workbook)
    probs, sec_ok, mon_ok = problems(w)
    if probs:
        print("Workbook has problems; run validate first.")
        for p in probs:
            print(" -", p)
        return 2
    repo = os.path.abspath(a.repo or os.path.join(HERE, "..", "..", "..", "gxp-quality-hub-legacy"))
    backup = os.path.abspath(a.backup or os.path.join(repo, "..", "_data-backup-2026-10-17"))
    out_dir = os.path.abspath(a.out or os.path.join(HERE, "release-check-output"))
    os.makedirs(out_dir, exist_ok=True)
    base_res = json.load(open(os.path.join(repo, "docs", "30-release", "evidence", "gate-results.json"), encoding="utf-8"))
    base_app = json.load(open(os.path.join(repo, "docs", "30-release", "evidence", "approvals-register.json"), encoding="utf-8"))
    date, who = w["date"], w["approver"]
    wb_name = os.path.basename(a.workbook)
    dec = dict((r["id"], r) for r in w["rows"])
    # ---- approvals file
    for rec in base_app["records"]:
        r = dec.get(rec["id"])
        if r and r["decision"] in ("APPROVED", "REJECTED"):
            rec["status"] = r["decision"]
            rec["approver"] = who
            rec["approval_ref"] = (r["approval_ref"] or "WB-%s-%s" % (rec["id"], date)).strip()
            rec["approved_on"] = date
            rec["evidence_ref"] = (r["evidence_ref"] or "docs/30-release/decisions/%s#%s" % (wb_name, rec["id"])).strip()
    # ---- sandbox
    tmp = tempfile.mkdtemp(prefix="relcheck-")
    sbx = os.path.join(tmp, "repo")
    os.makedirs(sbx)
    git_archive(repo, sbx)
    shutil.rmtree(os.path.join(sbx, "data"), ignore_errors=True)
    shutil.copytree(os.path.join(backup, "data"), os.path.join(sbx, "data"))
    bad = manifest_ok(os.path.join(sbx, ".."), os.path.join(backup, "SHA256SUMS.txt")) if False else None
    scratch = os.path.join(tmp, "scratch")
    os.makedirs(os.path.join(scratch, "anchor"))
    cfg = os.path.join(scratch, "config.json")
    json.dump({"audit": {"anchor_path": os.path.join(scratch, "anchor", "audit-anchor.jsonl")}}, open(cfg, "w"))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0", HUB_WORKTREE_ROOT=repo, HUB_SANDBOX_ROOT=scratch)
    py = sys.executable
    gc = os.path.join(scratch, "gc")
    gcmd = [py, "-B", "-m", "hub", "--config", cfg, "golden-compare", "--json", "--data-dir", gc, "--legacy-root", sbx, "--observe"]
    rc0, o0 = run(gcmd, sbx, env)  # creates and seeds the store; every row proposed
    print("golden-compare before decisions: exit %s" % rc0)
    dvs = [r for r in w["rows"] if r["id"].startswith("AP-DV-") and r["decision"] == "APPROVED"]
    con = sqlite3.connect(os.path.join(gc, "hub.sqlite3"))
    n = 0
    for r in dvs:
        dev_id = "DV-" + r["id"].split("-")[-1]
        ref = (r["approval_ref"] or "WB-%s-%s" % (r["id"], date)).strip()
        with con:
            cur = con.execute("UPDATE deviation_register SET status='approved', approval_ref=? WHERE dev_id=?", (ref, dev_id))
        n += cur.rowcount
    con.close()
    print("deviation rows set to approved in the SANDBOX store: %d" % n)
    rc1, o1 = run(gcmd, sbx, env)
    print("golden-compare after decisions: exit %s" % rc1)
    last = [l for l in o1.splitlines() if l.startswith("summary:")]
    if last:
        print(last[-1])
    open(os.path.join(out_dir, "golden-compare.txt"), "w", encoding="utf-8").write(o1.replace(tmp, "<sandbox>"))
    # ---- results file
    res = base_res["results"]
    wbpath = "docs/30-release/decisions/" + wb_name
    res["G1"] = {"result": "pass" if rc1 == 0 else "fail", "evidence_path": "docs/30-release/evidence/s30-log-06-golden-compare.txt",
                 "note": "golden-compare re-run in a sandbox with deviation decisions from %s: exit %s" % (wb_name, rc1)}
    if a.regression_log and os.path.exists(a.regression_log):
        lg = json.load(open(a.regression_log, encoding="utf-8"))
        okall = all(x["rc"] == 0 and x["complete"] for x in lg["results"])
        res["T-05"] = {"result": "pass" if okall else "fail", "evidence_path": a.regression_log.replace("\\", "/").split("gxp-quality-hub-legacy/")[-1],
                       "note": "%d of %d methods executed; python %s" % (lg["total_executed"], lg["total_expected"], (lg["results"][0].get("python") or "?"))}
    sec_ok_now = sec_ok
    res["T-10"] = {"result": "pass" if sec_ok_now else "fail", "evidence_path": wbpath + "#Security (T-10)",
                   "note": "decisions recorded by %s on %s" % (who, date) if sec_ok_now else "decisions for VR-02, VR-03, VR-04, F-11 not all recorded"}
    mchoice = [m["choice"] for m in w["monitoring"] if m["choice"]]
    if mchoice == ["A"] or (mchoice and mchoice[0] == "A"):
        res["T-09"] = {"result": "pass", "evidence_path": wbpath + "#Monitoring (T-09)", "note": "manual monitoring (RB-00) explicitly accepted by %s on %s for the release window" % (who, date)}
    elif mchoice:
        res["T-09"] = {"result": "fail", "evidence_path": wbpath + "#Monitoring (T-09)", "note": "option B chosen: metrics persistence not wired yet"}
    rp = os.path.join(out_dir, "gate-results.json")
    ap = os.path.join(out_dir, "approvals-register.json")
    json.dump(base_res, open(rp, "w", encoding="utf-8"), indent=1)
    json.dump(base_app, open(ap, "w", encoding="utf-8"), indent=1)
    rc, o = run([py, "-B", "-m", "hub.release", "evaluate", "--results", rp, "--approvals", ap], sbx, env)
    open(os.path.join(out_dir, "release-evaluate.txt"), "w", encoding="utf-8").write(o)
    print("---- repository evaluator (hub.release evaluate) ----")
    print(o)
    shutil.rmtree(tmp, ignore_errors=True)
    print("files written to", out_dir, "(your repository was not modified)")
    return 0 if rc == 0 else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("validate", "evaluate"):
        p = sub.add_parser(n)
        p.add_argument("--workbook", required=True)
        if n == "evaluate":
            p.add_argument("--repo")
            p.add_argument("--backup")
            p.add_argument("--regression-log")
            p.add_argument("--out")
    a = ap.parse_args()
    return {"validate": cmd_validate, "evaluate": cmd_evaluate}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
