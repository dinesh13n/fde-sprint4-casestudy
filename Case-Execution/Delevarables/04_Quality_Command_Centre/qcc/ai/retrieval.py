"""Keyword retrieval over the semantic layer (glossary, entities, rules, metrics, vocabularies, open decisions).
Deterministic and local: no embeddings service. Records whose epistemic_status is 'unknown' are kept but labelled.
"""
import json
import math
import re
from collections import Counter

TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-\.]*")
STOP = set("the a an of to and or in on for is are was be by with as at it this that what why how which who do does from into not no mean means meaning here explain tell me about define please can could should would i we our you".split())


def toks(text):
    return [t.lower().strip(".") for t in TOKEN.findall(text or "") if t.lower() not in STOP]


class Index(object):
    def __init__(self, sem):
        self.docs = []
        for g in sem.get("glossary", []):
            self._add("glossary:" + g["term"], "Glossary: %s - %s" % (g["term"], g["definition"]), g.get("source"))
        for e in sem["entities"]["items"]:
            self._add("entity:" + e["id"], "Entity %s: %s" % (e["id"], e["description"]), (e.get("evidence") or [""])[0], e.get("epistemic_status"))
        for r in sem["business_rules"]["items"]:
            self._add("rule:" + r["id"], "Rule %s (%s): %s" % (r["id"], r.get("strength", ""), r["statement"]), (r.get("evidence") or [""])[0],
                      r.get("epistemic_status"))
        for r in sem["spec_business_rules"]["items"]:
            self._add("rule:" + r["id"], "Spec rule %s: %s" % (r["id"], r["statement"]), r.get("evidence", [""])[0] if r.get("evidence") else "")
        for m in sem["metrics"]["items"]:
            base = m.get("baseline")
            self._add("metric:" + m["id"], "Metric %s %s. %s Formula: %s. Baseline (synthetic): %s" % (
                m["id"], m["name"], m.get("meaning", ""), m.get("formula", ""), json.dumps(base) if base else "n/a"),
                (m.get("evidence") or [""])[0], m.get("epistemic_status"))
        for t in sem["status_taxonomy"]["taxonomies"]:
            vals = ", ".join(str(v.get("value")) + (" (%s)" % (v.get("meaning") or v.get("note")) if (v.get("meaning") or v.get("note")) else "")
                             for v in (t.get("values") or []) if isinstance(v, dict))
            self._add("vocab:" + t["id"], "Vocabulary %s for %s: %s" % (t["id"], t.get("entity", ""), vals[:1200]), (t.get("evidence") or [""])[0])
        for d in sem["context_dependencies"]["open_decisions"]:
            self._add("decision:" + d["id"], "Open decision %s (%s): %s. %s" % (d["id"], d["status"], d["topic"], d.get("effect", "")), d.get("source_doc"))
        for w in sem["workflow_semantics"]["workflows"]:
            self._add("workflow:" + w["id"], "Workflow %s %s: %s" % (w["id"], w["name"], w.get("rule") or w.get("notes") or ", ".join(w.get("steps", []))),
                      (w.get("evidence") or [""])[0])
        n = len(self.docs)
        df = Counter()
        for d in self.docs:
            df.update(set(d["tokens"]))
        self.idf = dict((t, math.log(1 + n / (1.0 + c))) for t, c in df.items())

    def _add(self, did, text, source=None, status=None):
        self.docs.append({"id": did, "text": text, "source": source or "", "epistemic_status": status or "verified_fact", "tokens": toks(text)})

    def search(self, query, k=8):
        q = toks(query)
        if not q:
            return []
        scored = []
        for d in self.docs:
            tf = Counter(d["tokens"])
            s = sum(self.idf.get(t, 0) * (1 + math.log(tf[t])) for t in q if t in tf)
            # exact id mention boosts (e.g. "K-09", "ZH-05", "C00000012")
            s += sum(3.0 for t in q if d["id"].lower().endswith(":" + t))
            if s > 0:
                scored.append((s / (1 + 0.002 * len(d["tokens"])), d))
        scored.sort(key=lambda x: -x[0])
        return [dict(d, score=round(s, 2)) for s, d in scored[:k]]
