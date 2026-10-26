"""Advisory assistant: retrieve -> guard -> (optional) model call -> label -> log.

Modes
  model           ai.enabled and an API key exist: OpenAI / Azure OpenAI writes the answer from the retrieved context.
  retrieval-only  otherwise: the answer is the retrieved context itself, and model_calls_total stays 0.
Whatever the mode, the assistant has no write path: it cannot call the gate, the store or any action endpoint.
"""
import datetime
import json
import os
import threading
import time

from qcc.ai.client import ChatClient, ModelError
from qcc.ai.guard import ADVISORY_LABEL, SYSTEM_PROMPT, Guard
from qcc.ai.retrieval import Index


class Assistant(object):
    def __init__(self, settings, services, semantic, runtime_dir):
        self.s, self.svc = settings, services
        self.guard = Guard(settings)
        self.index = Index(semantic)
        self.client = ChatClient(settings)
        self.log_path = os.path.join(runtime_dir, "ai-calls.jsonl")
        self.counters = {"model_calls_total": 0, "model_errors_total": 0, "refused_action_requests_total": 0,
                         "retrieval_only_answers_total": 0, "flagged_untrusted_inputs_total": 0}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ context
    def _context(self, question, case_id=None, feed_id=None):
        blocks, flagged = [], 0
        if case_id:
            d = self.svc.case_detail(case_id)
            if d:
                c = d["case"]
                note, f = self.guard.untrusted(c["note"], "cases.note")
                flagged += f
                blocks.append({"id": "case:" + c["id"], "source": "legacy cases table (sandbox snapshot)", "text":
                               "Case %s site %s region %s segment %s created %s status %s severity %s amount %s (synthetic). Legacy priority rule says "
                               "'%s'; legacy manual-review rule says %s. D-OPS: %s. D-EVID: %s. D-FIN: %s. Events: %s. Policy exceptions: %s. "
                               "Partner-feed items referencing it: %d. Note: %s. Flags: %s." % (
                                   c["id"], c["site"], c["region"], c["segment"], c["created_at"], c["status"], c["severity"], c["amount"],
                                   c["legacy_priority"], c["legacy_manual_review"], d["definitions"]["D-OPS"], d["definitions"]["D-EVID"],
                                   d["definitions"]["D-FIN"], json.dumps([(e["event_type"], e["recorded_at"]) for e in d["events"]]),
                                   json.dumps([(x["policy_code"], x["outcome"]) for x in d["policy_exceptions"]]), len(d["feed_items"]),
                                   note, "; ".join(d["flags"]) or "none")})
        if feed_id:
            it = self.svc.intake_item(feed_id)
            if it:
                notes, f = self.guard.untrusted(it.get("notes_untrusted") or "", "partner_feeds.raw_json.notes")
                flagged += f
                blocks.append({"id": "feed:" + it["feed_id"], "source": "hub intake classification (sandbox)", "text":
                               "Feed item %s from partner %s, record kind %s, ref_id %s. Hub outcome %s, primary reason %s, all reasons %s, queue %s. "
                               "Notes: %s" % (it["feed_id"], it["partner"], it["record_kind"], it["ref_id"], it["outcome"], it["primary_reason"],
                                              it["all_reasons"], it["queue"], notes)})
        k = int(self.s.get("ai.retrieval.top_k", 8))
        for h in self.index.search(question + " " + (case_id or "") + " " + (feed_id or ""), k=k):
            blocks.append({"id": h["id"], "source": h["source"], "text": self.guard.scrub(h["text"]), "epistemic_status": h["epistemic_status"]})
        budget, out = int(self.s.get("ai.retrieval.max_context_chars", 12000)), []
        for b in blocks:
            if budget - len(b["text"]) < 0:
                break
            budget -= len(b["text"])
            out.append(b)
        for n, b in enumerate(out, 1):
            b["ref"] = "S%d" % n
        return out, flagged

    def _log(self, entry):
        if not self.s.get("ai.guardrails.log_prompts", True):
            entry = dict(entry, question="[not logged]")
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError:
            pass

    # ------------------------------------------------------------------ ask
    def ask(self, question, persona="reviewer", case_id=None, feed_id=None):
        question = (question or "").strip()[:2000]
        now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        base = {"label": ADVISORY_LABEL, "at": now, "persona": persona}
        if not question:
            return dict(base, mode="none", answer="Ask a question about a case, an exception or a definition.", citations=[])
        zh = self.guard.action_request(question)
        if zh:
            with self._lock:
                self.counters["refused_action_requests_total"] += 1
            self.svc.zone_h_attempt(zh.split("/")[0], persona, actor_kind="ai_assistant")
            ans = ("I can't do that. This is a Zone H action (%s): it is human-only, needs a named dispositioner holder, and no holder exists "
                   "(OPD-06). I can explain the case, the evidence that would be needed, or the rules that apply." % zh)
            self._log(dict(base, mode="refused", question=question, zone_h=zh))
            return dict(base, mode="refused", answer=ans, citations=[], zone_h=zh)
        blocks, flagged = self._context(question, case_id, feed_id)
        with self._lock:
            self.counters["flagged_untrusted_inputs_total"] += flagged
        cites = [{"ref": b["ref"], "id": b["id"], "source": b["source"], "epistemic_status": b.get("epistemic_status", "verified_fact")} for b in blocks]
        if not self.s.ai_ready():
            with self._lock:
                self.counters["retrieval_only_answers_total"] += 1
            if blocks:
                lines = ["[%s] %s" % (b["ref"], b["text"][:420]) for b in blocks[:5]]
                ans = "Retrieval-only mode (no API key, so no model call). Most relevant entries:\n" + "\n".join(lines)
            else:
                ans = "Retrieval-only mode. Nothing in the semantic layer matches the question; the answer is unknown."
            self._log(dict(base, mode="retrieval-only", question=question, citations=[c["id"] for c in cites]))
            return dict(base, mode="retrieval-only", answer=ans, citations=cites, untrusted_flagged=flagged)
        ctx = "\n\n".join("[%s] (%s; source: %s)\n%s" % (b["ref"], b["id"], b["source"], b["text"]) for b in blocks)
        messages = [{"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": "CONTEXT:\n%s\n\nQUESTION (from a %s): %s" % (ctx or "(none)", persona, self.guard.scrub(question))}]
        t0 = time.time()
        try:
            with self._lock:
                self.counters["model_calls_total"] += 1
            out = self.client.chat(messages)
        except ModelError as e:
            with self._lock:
                self.counters["model_errors_total"] += 1
            self._log(dict(base, mode="error", question=question, error=e.code))
            fallback = "\n".join("[%s] %s" % (b["ref"], b["text"][:300]) for b in blocks[:3])
            return dict(base, mode="error", error={"code": e.code, "message": e.message[:300]},
                        answer="The model call failed (%s). Showing retrieved context instead:\n%s" % (e.code, fallback), citations=cites)
        warnings = self.guard.check_answer(out["text"])
        self._log(dict(base, mode="model", question=question, model=out["model"], usage=out["usage"], latency_ms=out["latency_ms"],
                       citations=[c["id"] for c in cites], warnings=warnings))
        return dict(base, mode="model", answer=out["text"], citations=cites, model=out["model"], usage=out["usage"],
                    latency_ms=int((time.time() - t0) * 1000), warnings=warnings, untrusted_flagged=flagged)
