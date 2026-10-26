"""Read-only computations over the sandbox snapshot, using the hub's own deterministic modules where the hub has them.

Every figure carries the definition it uses (D-OPS / D-EVID / D-FIN) or is definition-independent. Nothing is combined across tags.
"""
import collections
import datetime
import decimal
import json
import re
import threading
import time

from qcc import evidence

AS_OF = datetime.datetime(2025, 12, 19, 7, 11, tzinfo=datetime.timezone.utc)
LABEL = "synthetic, unvalidated"
INSTRUCTION_LIKE = re.compile(r"(?i)(system note|ignore (all|previous)|disregard|auto[- ]?approve|you are now|act as|override)")
LEGACY_MONTH_END_SQL = "SELECT SUM(c.amount) FROM cases c LEFT JOIN events e ON e.case_id = c.id WHERE c.created_at <= ?"
HUB_MONTH_END_SQL = "SELECT id, amount, created_at FROM cases ORDER BY id"


def _ts(s):
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))


def _bucket(days):
    if days <= 90:
        return "<=90 d"
    if days <= 365:
        return "91-365 d"
    if days <= 730:
        return "366-730 d"
    return ">730 d"


def _pct(n, d):
    return round(100.0 * n / d, 2) if d else None


class Services(object):
    def __init__(self, snap, hub, semantic):
        self.snap, self.hub, self.sem = snap, hub, semantic
        self._lock = threading.Lock()
        self._intake = None
        self._case_ids = None
        self.audit = []  # in-memory gate-attempt log for this run (also written by the server to runtime/)

    # ------------------------------------------------------------------ helpers
    def case_ids(self):
        if self._case_ids is None:
            self._case_ids = set(r[0] for r in self.snap.q("SELECT id FROM cases"))
        return self._case_ids

    def _case_row(self, r):
        cid, acct, seg, site, region, created, status, sev, amount, note, ver = r
        return {
            "id": cid, "account_id": acct, "segment": seg, "site": site, "region": region, "created_at": created,
            "status": status, "severity": sev, "amount": "%.2f" % amount, "note": note, "version": ver,
            "legacy_priority": self.hub.legacy.priority(status, sev, amount),
            "legacy_manual_review": bool(self.hub.legacy.manual_review_required(status, sev)),
            "d_ops_closed": status == "CLOSED",
            "age_days": int((AS_OF - _ts(created)).total_seconds() // 86400),
        }

    # ------------------------------------------------------------------ overview
    def overview(self):
        rows = [self._case_row(r) for r in self.snap.q("SELECT * FROM cases ORDER BY id")]
        n = len(rows)
        status = collections.Counter(r["status"] for r in rows)
        open_rows = [r for r in rows if not r["d_ops_closed"]]
        by_site = collections.Counter(r["site"] for r in open_rows)
        ageing = collections.Counter(_bucket(r["age_days"]) for r in open_rows)
        months = collections.Counter(r["created_at"][:7] for r in rows)
        sev = collections.Counter(r["severity"] for r in rows)
        feeds = self.snap.q("SELECT ref_id FROM partner_feeds")
        unmatched = sum(1 for (ref,) in feeds if ref not in self.case_ids())
        dev = self.snap.q("SELECT status, root_cause FROM deviations")
        dev_closed = [d for d in dev if d[0] == "CLOSED"]
        capa = collections.Counter(s for (s,) in self.snap.q("SELECT state FROM capa_actions"))
        me = self.month_end("2025-12-31")
        ages = sorted(r["age_days"] for r in open_rows)
        intake = self.intake_preview(summary_only=True)
        return {
            "label": LABEL, "as_of": AS_OF.isoformat(),
            "cases": n,
            "status_counts": dict(status),
            "severity_counts": dict(sev),
            "backlog_d_ops": {"value": len(open_rows), "denominator": n, "definition_tag": "D-OPS", "by_site": dict(sorted(by_site.items())),
                              "ageing": {k: ageing.get(k, 0) for k in ("<=90 d", "91-365 d", "366-730 d", ">730 d")},
                              "age_median_days": float(self.hub.values.median([decimal.Decimal(a) for a in ages])) if ages else None},
            "backlog_d_evid": {"value": None, "reason": "no evidence or approver timestamps exist (Unknown)", "definition_tag": "D-EVID"},
            "backlog_d_fin": {"value": None, "reason": "D-FIN is undefined (OPD-01)", "definition_tag": "D-FIN"},
            "cases_per_month": dict(sorted(months.items())),
            "reopen_rate": {"value": _pct(status.get("REOPENED", 0), n), "n": status.get("REOPENED", 0), "denominator": n},
            "manual_review_share": {"value": _pct(sum(r["legacy_manual_review"] for r in rows), n), "rule": "app/legacy_logic.manual_review_required"},
            "unmatched_feed_rate": {"value": _pct(unmatched, len(feeds)), "n": unmatched, "denominator": len(feeds)},
            "deviations_closed_without_root_cause": {"value": _pct(sum(1 for d in dev_closed if d[1] is None), len(dev_closed)),
                                                     "n": sum(1 for d in dev_closed if d[1] is None), "denominator": len(dev_closed)},
            "capa_overdue_share": {"value": _pct(capa.get("OVERDUE", 0), capa.get("OVERDUE", 0) + capa.get("OPEN", 0)),
                                   "n": capa.get("OVERDUE", 0), "denominator": capa.get("OVERDUE", 0) + capa.get("OPEN", 0)},
            "month_end": me,
            "intake": intake,
            "zone_h": {"actions": 10, "holders": 0},
            "release": {"verdict": evidence.RELEASE["verdict"], "approvals": evidence.RELEASE["approvals"]},
        }

    # ------------------------------------------------------------------ cases
    def cases(self, site=None, status=None, severity=None, q=None, limit=500):
        rows = [self._case_row(r) for r in self.snap.q("SELECT * FROM cases ORDER BY created_at DESC")]
        if site:
            rows = [r for r in rows if r["site"] == site]
        if status:
            rows = [r for r in rows if r["status"] == status]
        if severity:
            rows = [r for r in rows if r["severity"] == severity]
        if q:
            ql = q.lower()
            rows = [r for r in rows if ql in r["id"].lower() or ql in r["note"].lower() or ql in r["account_id"].lower()]
        return {"label": LABEL, "count": len(rows), "items": rows[:limit],
                "facets": {"site": sorted(set(r[0] for r in self.snap.q("SELECT DISTINCT site FROM cases"))),
                           "status": sorted(set(r[0] for r in self.snap.q("SELECT DISTINCT status FROM cases"))),
                           "severity": sorted(set(r[0] for r in self.snap.q("SELECT DISTINCT severity FROM cases")))}}

    def case_detail(self, cid):
        r = self.snap.q("SELECT * FROM cases WHERE id = ?", (cid,))
        if not r:
            return None
        case = self._case_row(r[0])
        events = []
        for eid, _, rec, et, payload in self.snap.q("SELECT * FROM events WHERE case_id = ? ORDER BY recorded_at, id", (cid,)):
            try:
                p = json.loads(payload)
            except ValueError:
                p = {"raw": payload}
            events.append({"id": eid, "recorded_at": rec, "event_type": et, "payload": p})
        exc = [dict(zip(("exception_id", "ref_id", "policy_code", "outcome", "actor", "recorded_at", "explanation"), x))
               for x in self.snap.q("SELECT * FROM policy_exceptions WHERE ref_id = ? ORDER BY recorded_at", (cid,))]
        feeds = self.snap.q("SELECT feed_id, partner, record_kind, source_ts, processing_status FROM partner_feeds WHERE ref_id = ? ORDER BY source_ts", (cid,))
        reopened_without_event = case["status"] == "REOPENED" and not any(e["event_type"] == "REOPEN" for e in events)
        return {
            "label": LABEL, "case": case, "events": events, "policy_exceptions": exc,
            "feed_items": [dict(zip(("feed_id", "partner", "record_kind", "source_ts", "processing_status"), f)) for f in feeds],
            "definitions": {
                "D-OPS": "closed" if case["d_ops_closed"] else "not closed",
                "D-EVID": "unknown: no evidence record or approver exists in the legacy data",
                "D-FIN": "undefined (OPD-01)",
            },
            "flags": (["LEGACY_UNEVIDENCED_REOPEN: status REOPENED with no reopen event (SBR-DEC-05)"] if reopened_without_event else []),
            "zone_h_note": "Disposition of this case is a Zone H action (ZH-01..ZH-03). It needs a named human holder; none exists.",
        }

    # ------------------------------------------------------------------ intake (the hub's own validation)
    def _run_intake(self):
        H = self.hub
        prof = H.profiles.PROFILES["partner_feed"]
        cases = self.case_ids()
        seen, items, dup = {}, [], 0
        t0 = time.time()
        rows = self.snap.q("SELECT feed_id, partner, schema_rev, source_ts, ingest_ts, ref_id, record_kind, raw_json, processing_status "
                           "FROM partner_feeds ORDER BY ingest_ts, feed_id")
        for fid, partner, rev, sts, its, ref, kind, raw, pst in rows:
            ch = H.canon.content_hash(rev, raw)
            ik, complete = H.canon.identity_key("partner_feed", partner, kind, ref, sts, fid, ch)
            d = dict(source_key=fid, partner=partner, schema_rev=rev, source_ts=sts, ref_id=ref, record_kind=kind, payload_text=raw)
            reasons, detail, facts = H.validate.validate(prof, d)
            if ik in seen:
                if seen[ik] == ch:
                    dup += 1
                    continue
                reasons.add("REVISED_CONFLICT")
            else:
                seen[ik] = ch
            if not (reasons & H.reasons.NO_MATCH_REASONS) and ref not in cases:
                reasons.add("UNMATCHED_REF")
            k = H.reasons.classify(reasons)
            notes = None
            if isinstance(facts.get("payload"), dict):
                notes = facts["payload"].get("notes")
            items.append({"feed_id": fid, "partner": partner, "record_kind": kind, "ref_id": ref, "source_ts": sts,
                          "legacy_processing_status": pst, "outcome": k["outcome"], "primary_reason": k["primary_reason"],
                          "all_reasons": k["all_reasons"], "queue": k["queue"],
                          "notes_untrusted": notes if isinstance(notes, str) else None,
                          "instruction_like": bool(isinstance(notes, str) and INSTRUCTION_LIKE.search(notes))})
        return {"rows_delivered": len(rows), "noop_duplicate": dup, "items": items, "identity": seen,
                "elapsed_ms": int((time.time() - t0) * 1000)}

    def intake_preview(self, summary_only=False, queue=None, reason=None, limit=200):
        with self._lock:
            if self._intake is None:
                self._intake = self._run_intake()
        r = self._intake
        items = r["items"]
        outcome = collections.Counter(i["outcome"] for i in items)
        queues = collections.Counter(i["queue"] for i in items if i["queue"])
        primary = collections.Counter(i["primary_reason"] for i in items if i["primary_reason"])
        out = {"label": LABEL, "rows_delivered": r["rows_delivered"], "stored_items": len(items), "noop_duplicate": r["noop_duplicate"],
               "outcomes": dict(outcome), "queues": {q: queues.get(q, 0) for q in self.hub.reasons.QUEUES},
               "exception_queue_total": sum(queues.values()),
               "instruction_like_notes": sum(1 for i in items if i["instruction_like"]), "elapsed_ms": r["elapsed_ms"],
               "engine": "hub.intake.validate + hub.intake.reasons.classify + hub.intake.canon.identity_key (the built hub code)"}
        if summary_only:
            return out
        out["precedence"] = [{"rank": n + 1, "code": c, "class": self.hub.reasons.CATALOG[c][0], "queue": self.hub.reasons.CATALOG[c][1],
                              "primary_count": primary.get(c, 0)} for n, c in enumerate(self.hub.reasons.PRECEDENCE)]
        sel = items
        if queue:
            sel = [i for i in sel if i["queue"] == queue]
        if reason:
            sel = [i for i in sel if reason in i["all_reasons"]]
        out["filtered_count"] = len(sel)
        out["items"] = sel[:limit]
        return out

    def intake_item(self, feed_id):
        self.intake_preview(summary_only=True)
        for i in self._intake["items"]:
            if i["feed_id"] == feed_id:
                return i
        return None

    def replay(self):
        """K-07: re-deliver every row already processed. Expected: all NOOP_DUPLICATE, queue sizes and totals unchanged."""
        self.intake_preview(summary_only=True)
        H, seen = self.hub, self._intake["identity"]
        before = self.intake_preview(summary_only=True)
        noop = conflict = new = 0
        t0 = time.time()
        for fid, partner, rev, sts, ref, kind, raw in self.snap.q(
                "SELECT feed_id, partner, schema_rev, source_ts, ref_id, record_kind, raw_json FROM partner_feeds"):
            ch = H.canon.content_hash(rev, raw)
            ik, _ = H.canon.identity_key("partner_feed", partner, kind, ref, sts, fid, ch)
            if ik in seen and seen[ik] == ch:
                noop += 1
            elif ik in seen:
                conflict += 1
            else:
                new += 1
        after = self.intake_preview(summary_only=True)
        return {"label": LABEL, "redelivered": noop + conflict + new, "noop_duplicate": noop, "would_conflict": conflict, "new": new,
                "queue_total_before": before["exception_queue_total"], "queue_total_after": after["exception_queue_total"],
                "delta": after["exception_queue_total"] - before["exception_queue_total"], "elapsed_ms": int((time.time() - t0) * 1000),
                "note": "Rows whose identity was first seen with different content count as would_conflict (REVISED_CONFLICT), never as new work."}

    # ------------------------------------------------------------------ month-end (RC-8)
    def month_end(self, cutoff):
        if not cutoff or not re.match(r"^\d{4}-\d{2}-\d{2}$", cutoff):
            return {"error": "E-MET-CUTOFF-REQUIRED", "message": "An explicit cut-off date is required (OPD-08: there is no default)."}
        cut = cutoff + "T23:59:59+00:00"
        legacy = self.snap.q(LEGACY_MONTH_END_SQL, (cut,))[0][0] or 0.0
        total, n, errors = decimal.Decimal("0"), 0, collections.Counter()
        for cid, amount, created in self.hub.sources.CasesAmountSource(self.snap.con()).read():
            if created > cut:
                continue
            d, err = self.hub.sources.parse_amount(amount)
            if err:
                errors[err] += 1
                continue
            total += d
            n += 1
        hub_total = total.quantize(decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_EVEN)
        joined_rows = self.snap.q("SELECT COUNT(*) FROM cases c LEFT JOIN events e ON e.case_id = c.id WHERE c.created_at <= ?", (cut,))[0][0]
        diff = decimal.Decimal(repr(legacy)).quantize(decimal.Decimal("0.01")) - hub_total
        return {"label": LABEL, "cutoff": cutoff, "legacy": {"value": "%.2f" % legacy, "sql": LEGACY_MONTH_END_SQL, "rows_summed": joined_rows},
                "hub": {"value": str(hub_total), "sql": HUB_MONTH_END_SQL, "rows_summed": n, "errors": dict(errors),
                        "engine": "hub.metrics.sources.CasesAmountSource + parse_amount (exact Decimal, ROUND_HALF_EVEN)"},
                "difference": str(diff), "inflation_pct": float(round(diff / hub_total * 100, 1)) if hub_total else None,
                "explanation": "The legacy report joins cases to events; a case with k events is summed k times (join fan-out)."}

    # ------------------------------------------------------------------ definitions and semantic layer
    def definitions(self):
        tax = dict((t["id"], t) for t in self.sem["status_taxonomy"]["taxonomies"])
        closed = []
        for t in self.sem["status_taxonomy"]["taxonomies"]:
            for v in t.get("values") or []:
                if isinstance(v, dict) and v.get("value") == "CLOSED":
                    closed.append({"vocabulary": t["id"], "entity": t.get("entity"), "meaning": v.get("note") or v.get("meaning") or "",
                                   "legacy_column": t.get("legacy_column")})
        od = self.sem["context_dependencies"]["open_decisions"]
        return {"label": LABEL, "definition_tags": tax["vocab.definition_tag"]["values"], "closed_in_vocabularies": closed,
                "cross_vocabulary_mapping": self.sem["status_taxonomy"]["cross_vocabulary_mapping"],
                "autonomy_levels": tax["vocab.autonomy_level"]["values"], "roles": tax["vocab.role"]["values"],
                "open_decisions": od, "vocabulary_count": len(tax), "entity_count": len(self.sem["entities"]["items"])}

    # ------------------------------------------------------------------ Zone H (human-only actions)
    def zone_h(self):
        tax = dict((t["id"], t) for t in self.sem["status_taxonomy"]["taxonomies"])
        acc = self.sem["access_semantics"]["zone_h"]
        return {"label": LABEL, "actions": tax["vocab.zone_h_action"]["values"], "holders": acc["holders"], "rule": acc["rule"],
                "open_decision": acc.get("open_decision"), "attempts": self.audit[-25:]}

    def zone_h_attempt(self, action, persona, actor_kind="human"):
        codes = [v["value"] for v in self.zone_h()["actions"]]
        now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        if action not in codes:
            res = {"accepted": False, "code": "E-GATE-UNKNOWN-ACTION"}
        elif actor_kind != "human":
            res = {"accepted": False, "code": "E-GATE-NOT-AUTHORISED", "reason": "Service and AI actors can never perform a Zone H action (FR-GATE-03)."}
        elif persona != "dispositioner":
            res = {"accepted": False, "code": "E-GATE-NOT-AUTHORISED", "reason": "Only the dispositioner role can hold Zone H."}
        elif not self.zone_h()["holders"]:
            res = {"accepted": False, "code": "E-GATE-NO-HOLDERS", "reason": "zone_h.holders ships empty; no human has been named (OPD-06)."}
        else:
            res = {"accepted": False, "code": "E-GATE-REAUTH-REQUIRED"}
        entry = dict(res, action=action, persona=persona, actor_kind=actor_kind, at=now)
        self.audit.append(entry)
        return entry

    # ------------------------------------------------------------------ release and evidence
    def release(self):
        return {"label": LABEL, "release": evidence.RELEASE, "engineering": evidence.ENGINEERING,
                "root_causes": [dict(zip(("id", "cause", "mechanism"), r)) for r in evidence.ROOT_CAUSES],
                "root_cause_source": evidence.ROOT_CAUSE_SOURCE}
