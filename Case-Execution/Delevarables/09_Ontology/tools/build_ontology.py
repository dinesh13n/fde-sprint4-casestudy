#!/usr/bin/env python3
"""Build the GxP Quality Hub ontology (OWL2 + SKOS, Turtle) from the semantic-layer YAMLs.

Usage: build_ontology.py [--sl DIR] [--db legacy.sqlite3] [--out DIR]
Outputs (in --out): gxp-ontology.ttl (schema), gxp-instances.ttl (synthetic data, optional),
                    ontology.json (compact model for the HTML explorer).
Everything is derived from the YAMLs; nothing is invented here. Synthetic data only.
"""
import argparse, json, re, sqlite3, sys
from pathlib import Path
import yaml
from rdflib import Graph, Namespace, Literal, RDF, RDFS, OWL, XSD, SKOS, DCTERMS, URIRef

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("--sl", default=str(HERE.parent.parent / "semantic-layer"))
ap.add_argument("--db", default=None)
ap.add_argument("--out", default=str(HERE.parent))
a = ap.parse_args()
SL, OUT = Path(a.sl), Path(a.out)
Y = lambda n: yaml.safe_load(open(SL / n, encoding="utf-8"))

GX = Namespace("https://example.org/gxp-hub/onto#")     # schema (classes, properties)
VC = Namespace("https://example.org/gxp-hub/vocab/")    # SKOS vocabularies
ID = Namespace("https://example.org/gxp-hub/id/")       # individuals / instance data
slug = lambda s: re.sub(r"[^A-Za-z0-9_]+", "_", str(s)).strip("_")

def bind(g):
    for p, n in (("gx", GX), ("vc", VC), ("id", ID), ("skos", SKOS), ("owl", OWL), ("dcterms", DCTERMS)):
        g.bind(p, n)

ent, rel, tax = Y("entities.yaml"), Y("relationships.yaml"), Y("status-taxonomy.yaml")
wf, acc, met, br = Y("workflow-semantics.yaml"), Y("access-semantics.yaml"), Y("metrics.yaml"), Y("business-rules.yaml")

g = Graph(); bind(g)
onto = URIRef("https://example.org/gxp-hub/onto")
g.add((onto, RDF.type, OWL.Ontology))
g.add((onto, RDFS.label, Literal("GxP Quality Hub ontology (demo)")))
g.add((onto, RDFS.comment, Literal(
    "Generated from the semantic layer of gxp-quality-hub-legacy. SYNTHETIC, UNVALIDATED: demo of the model, "
    "not a validated GxP record. Statuses carry no business meaning until a policy is adopted (Zone H ZH-05).")))
g.add((onto, OWL.versionInfo, Literal(str(ent.get("semantic_layer_version")))))

def prov(s, item):
    if item.get("epistemic_status"): g.add((s, GX.epistemicStatus, Literal(item["epistemic_status"])))
    for ev in item.get("evidence") or []: g.add((s, GX.evidence, Literal(ev)))

# annotation / helper properties
for p, lab in (("epistemicStatus", "epistemic status"), ("evidence", "evidence reference"),
               ("legacySource", "legacy source"), ("mutability", "mutability"), ("sensitivity", "sensitivity class"),
               ("identityPattern", "identity pattern"), ("legacyColumn", "legacy column"), ("enforcement", "enforcement"),
               ("cardinality", "cardinality"), ("joinKey", "join key"), ("statusVocabulary", "status vocabulary"),
               ("category", "category")):
    g.add((GX[p], RDF.type, OWL.AnnotationProperty)); g.add((GX[p], RDFS.label, Literal(lab)))

VOCAB_ATTR = {("Case","status"):"vocab.case_status",("Case","segment"):"vocab.case_segment",("Case","site"):"vocab.site",
  ("Case","region"):"vocab.region",("Case","severity"):"vocab.severity",("Batch","qa_status"):"vocab.batch_qa_status",
  ("LabResult","test_status"):"vocab.lab_test_status",("Deviation","status"):"vocab.deviation_status",
  ("Deviation","classification"):"vocab.deviation_classification",("Deviation","root_cause"):"vocab.quality_fault",
  ("CAPA","state"):"vocab.capa_state"}
# ---------- classes ----------
cats = {}
for e in ent["items"]:
    cats.setdefault(e["category"], []).append(e["id"])
for c in cats:
    cu = GX["Category_" + slug(c)]
    g.add((cu, RDF.type, OWL.Class)); g.add((cu, RDFS.label, Literal(c.replace("_", " ").title())))
    g.add((cu, RDFS.comment, Literal("Grouping class: entity category '%s'." % c)))
model = {"classes": [], "relations": [], "vocabs": [], "roles": [], "zoneh": [], "metrics": [], "rules": [], "workflows": []}
for e in ent["items"]:
    cu = GX[e["id"]]
    g.add((cu, RDF.type, OWL.Class)); g.add((cu, RDFS.label, Literal(e["id"])))
    g.add((cu, RDFS.subClassOf, GX["Category_" + slug(e["category"])]))
    g.add((cu, RDFS.comment, Literal(" ".join(e["description"].split()))))
    g.add((cu, GX.category, Literal(e["category"])))
    for k in ("legacy_source", "mutability", "sensitivity"):
        if e.get(k): g.add((cu, GX[{"legacy_source": "legacySource"}.get(k, k)], Literal(str(e[k]))))
    idn = e.get("identity") or {}
    if idn.get("pattern"): g.add((cu, GX.identityPattern, Literal(idn["pattern"])))
    if idn.get("legacy_column"): g.add((cu, GX.legacyColumn, Literal(idn["legacy_column"])))
    if e.get("vocabulary"):
        vs = e["vocabulary"] if isinstance(e["vocabulary"], list) else [e["vocabulary"]]
        for v in vs: g.add((cu, GX.statusVocabulary, VC[slug(v)]))
    prov(cu, e)
    attrs = e.get("attributes") or {}
    for an, ad in attrs.items():
        pu = GX["%s_%s" % (e["id"], an)]
        isv = (e["id"], an) in VOCAB_ATTR
        g.add((pu, RDF.type, OWL.ObjectProperty if isv else OWL.DatatypeProperty)); g.add((pu, RDFS.label, Literal("%s.%s" % (e["id"], an))))
        g.add((pu, RDFS.domain, cu)); g.add((pu, RDFS.comment, Literal(" ".join(str(ad).split()))))
        g.add((pu, RDFS.range, SKOS.Concept if isv else XSD.string))
        if isv: g.add((pu, GX.statusVocabulary, VC[slug(VOCAB_ATTR[(e["id"], an)])]))
    model["classes"].append({"id": e["id"], "category": e["category"], "description": " ".join(e["description"].split()),
        "identity": idn, "attributes": {k: " ".join(str(v).split()) for k, v in attrs.items()},
        "vocabulary": e.get("vocabulary"), "mutability": e.get("mutability"), "sensitivity": e.get("sensitivity"),
        "epistemic": e.get("epistemic_status"), "legacy_source": e.get("legacy_source")})

# ---------- object properties from relationships ----------
for r in rel["items"]:
    pu = GX[r["id"].replace("-", "_")]
    g.add((pu, RDF.type, OWL.ObjectProperty))
    g.add((pu, RDFS.label, Literal(r["predicate"])))
    g.add((pu, RDFS.domain, GX[r["from"]])); g.add((pu, RDFS.range, GX[r["to"]]))
    g.add((pu, GX.cardinality, Literal(str(r["cardinality"]))))
    g.add((pu, GX.joinKey, Literal(str(r["key"]))))
    g.add((pu, GX.enforcement, Literal(r["enforcement"])))
    if r.get("crosswalk_link_type"): g.add((pu, GX.crosswalkLinkType, Literal(r["crosswalk_link_type"])))
    if str(r["cardinality"]).startswith("many-to-one") or str(r["cardinality"]).startswith("one-to-zero"):
        g.add((pu, RDF.type, OWL.FunctionalProperty)) if str(r["cardinality"]).startswith("many-to-one") else None
    prov(pu, r)
    model["relations"].append({k: r.get(k) for k in ("id", "from", "predicate", "to", "cardinality", "key", "enforcement", "epistemic_status")}
                              | {"link": r.get("crosswalk_link_type")})
model["known_gaps"] = [{"id": x["id"], "statement": x["statement"]} for x in rel.get("known_gaps", [])]

# ---------- SKOS vocabularies ----------
entity_of_vocab = {}
for t in tax["taxonomies"]:
    sch = VC[slug(t["id"])]
    g.add((sch, RDF.type, SKOS.ConceptScheme))
    g.add((sch, SKOS.prefLabel, Literal(t["id"])))
    g.add((sch, GX.legacyColumn, Literal(str(t.get("legacy_column", "")))))
    g.add((sch, DCTERMS.creator, Literal(str(t.get("owner", "unassigned")))))
    g.add((sch, GX.meaningStatus, Literal(str(t.get("meaning_status", "unknown")))))
    if t.get("entity"): g.add((sch, GX.describesClass, GX[t["entity"]]))
    prov(sch, t)
    vals = []
    for v in t["values"]:
        cu = VC[slug(t["id"]) + "/" + slug(v["value"])]
        g.add((cu, RDF.type, SKOS.Concept)); g.add((cu, SKOS.inScheme, sch)); g.add((cu, SKOS.topConceptOf, sch))
        g.add((cu, SKOS.prefLabel, Literal(str(v["value"]))))
        if v.get("note"): g.add((cu, SKOS.note, Literal(" ".join(str(v["note"]).split()))))
        if v.get("count_in_baseline") is not None: g.add((cu, GX.countInBaseline, Literal(v["count_in_baseline"], datatype=XSD.integer)))
        for rt in v.get("role_tags") or []: g.add((cu, GX.roleTag, Literal(rt)))
        vals.append({"value": str(v["value"]), "count": v.get("count_in_baseline"), "tags": v.get("role_tags") or []})
    model["vocabs"].append({"id": t["id"], "entity": t.get("entity"), "owner": t.get("owner"), "meaning": t.get("meaning_status"),
                            "legacy_column": t.get("legacy_column"), "values": vals})
for p in ("meaningStatus", "countInBaseline", "roleTag", "crosswalkLinkType", "describesClass"):
    g.add((GX[p], RDF.type, OWL.AnnotationProperty if p != "describesClass" else OWL.ObjectProperty))
# explicit "no automatic mapping" rule on the scheme level
g.add((GX.CrossVocabularyMappingPolicy, RDF.type, OWL.Class))
g.add((GX.CrossVocabularyMappingPolicy, RDFS.comment, Literal(tax["cross_vocabulary_mapping"]["statement"])))
# CLOSED appears in several vocabularies; deliberately NOT owl:sameAs / skos:exactMatch
closed = [VC[slug(t["id"]) + "/CLOSED"] for t in tax["taxonomies"] if any(str(v["value"]) == "CLOSED" for v in t["values"])]
for c in closed: g.add((c, SKOS.note, Literal("Same label as CLOSED in other vocabularies, NOT the same meaning. No skos:exactMatch is asserted (ZH-05).")))
model["closed_in"] = len(closed)

# ---------- roles, zone H, classification ----------
g.add((GX.Role, RDF.type, OWL.Class))
for r in acc["roles"]:
    ru = ID["role/" + slug(r["id"])]
    g.add((ru, RDF.type, GX.Role)); g.add((ru, RDFS.label, Literal(r["id"]))); g.add((ru, RDFS.comment, Literal("May: " + r["may"])))
    model["roles"].append({"id": r["id"], "may": r["may"]})
zh = acc["zone_h"]
zvocab = next(t for t in tax["taxonomies"] if t["id"] == "vocab.zone_h_action")
g.add((GX.HumanHolder, RDF.type, OWL.Class))
for v in zvocab["values"]:
    zu = ID["zoneh/" + slug(v["value"])]
    g.add((zu, RDF.type, GX.ZoneHAction)); g.add((zu, RDFS.label, Literal(str(v["value"]))))
    if v.get("note"): g.add((zu, RDFS.comment, Literal(" ".join(str(v["note"]).split()))))
    g.add((zu, GX.requiresNamedHuman, Literal(True))); g.add((zu, GX.holderCount, Literal(len(zh.get("holders") or []), datatype=XSD.integer)))
    model["zoneh"].append({"id": str(v["value"]), "note": " ".join(str(v.get("note", "")).split())})
for p in ("requiresNamedHuman", "holderCount"): g.add((GX[p], RDF.type, OWL.DatatypeProperty))
g.add((GX.ZoneHAction, RDFS.comment, Literal(zh["rule"])))
model["zoneh_rule"] = zh["rule"]; model["zoneh_holders"] = len(zh.get("holders") or [])

# ---------- metrics ----------
g.add((GX.definitionClass, RDF.type, OWL.AnnotationProperty))
for m in met["items"]:
    mu = ID["metric/" + slug(m["id"])]
    g.add((mu, RDF.type, GX.MetricDefinition)); g.add((mu, RDFS.label, Literal("%s %s" % (m["id"], m["name"]))))
    g.add((mu, RDFS.comment, Literal(" ".join(str(m.get("meaning","")).split()))))
    g.add((mu, GX.definitionClass, Literal(str(m.get("definition_class","none")))))
    g.add((mu, GX.computableToday, Literal(bool(m.get("computable_today", False)))))
    if m.get("unit"): g.add((mu, GX.unit, Literal(str(m["unit"]))))
    if m.get("formula"): g.add((mu, GX.formula, Literal(str(m["formula"]))))
    prov(mu, m)
    model["metrics"].append({"id": m["id"], "name": m["name"], "kind": m.get("kind",""), "cls": str(m.get("definition_class","none")),
                             "computable": bool(m.get("computable_today", False)), "meaning": " ".join(str(m.get("meaning","")).split()),
                             "baseline": (m.get("baseline") or {}).get("value")})
for p in ("computableToday", "unit", "formula"): g.add((GX[p], RDF.type, OWL.DatatypeProperty))

# ---------- business rules ----------
g.add((GX.BusinessRule, RDF.type, OWL.Class)); g.add((GX.appliesTo, RDF.type, OWL.ObjectProperty))
for b in br["items"]:
    bu = ID["rule/" + slug(b["id"])]
    g.add((bu, RDF.type, GX.BusinessRule)); g.add((bu, RDFS.label, Literal(b["id"])))
    g.add((bu, RDFS.comment, Literal(" ".join(b["statement"].split())))); g.add((bu, GX.strength, Literal(b["strength"])))
    g.add((bu, GX.ruleCategory, Literal(b["category"])))
    ap_ = [x for x in (b.get("applies_to") or []) if any(x == e["id"] for e in ent["items"])]
    for x in ap_: g.add((bu, GX.appliesTo, GX[x]))
    for x in b.get("implements") or []: g.add((bu, GX.implements, Literal(x)))
    prov(bu, b)
    model["rules"].append({"id": b["id"], "category": b["category"], "strength": b["strength"], "applies": b.get("applies_to") or [],
                           "statement": " ".join(b["statement"].split())})
for p in ("strength", "ruleCategory", "implements"): g.add((GX[p], RDF.type, OWL.AnnotationProperty))

# ---------- workflows ----------
g.add((GX.Workflow, RDF.type, OWL.Class)); g.add((GX.usesVocabulary, RDF.type, OWL.ObjectProperty))
for w in wf["workflows"]:
    wu = ID["workflow/" + slug(w["id"])]
    g.add((wu, RDF.type, GX.Workflow)); g.add((wu, RDFS.label, Literal(w["name"])))
    g.add((wu, RDFS.comment, Literal(" ".join(str(w.get("notes", "")).split()))))
    for s_ in w.get("states_ref") or []: g.add((wu, GX.usesVocabulary, VC[slug(s_)]))
    model["workflows"].append({"id": w["id"], "name": w["name"], "vocabs": w.get("states_ref") or [], "notes": " ".join(str(w.get("notes", "")).split())})

g.serialize(OUT / "gxp-ontology.ttl", format="turtle")
print("schema triples:", len(g))

# ---------- instance data (synthetic) ----------
inst = Graph(); bind(inst)
inst_count = {}
if a.db and Path(a.db).exists():
    c = sqlite3.connect("file:%s?mode=ro" % a.db, uri=True); c.row_factory = sqlite3.Row
    known = {t["id"]: {slug(str(v["value"])) for v in t["values"]} for t in tax["taxonomies"]}
    def concept(vocab, val):
        if val is None: return None
        k = slug(val)
        return VC[slug(vocab) + "/" + k] if k in known.get(vocab, ()) else None
    def lit(x):
        return Literal(x) if x is not None else None
    def add_row(cls, key, row, attrs, vocabmap=None):
        u = ID["%s/%s" % (cls.lower(), slug(key))]
        inst.add((u, RDF.type, GX[cls])); inst.add((u, RDFS.label, Literal(str(key))))
        for col in attrs:
            v = row[col]
            if v is None: continue
            if vocabmap and col in vocabmap:
                cu = concept(vocabmap[col], v)
                if cu: inst.add((u, GX["%s_%s" % (cls, col)], cu)); continue
            inst.add((u, GX["%s_%s" % (cls, col)], Literal(v)))
        inst_count[cls] = inst_count.get(cls, 0) + 1
        return u
    # re-declare object-valued data props used for vocab links
    for r_ in c.execute("select * from materials"):
        add_row("Material", r_["material_id"], r_, ["material_name", "source_site", "spec_version"])
    for r_ in c.execute("select * from batch_records"):
        u = add_row("Batch", r_["batch_id"], r_, ["batch_site", "observed_assay", "assay_unit", "qa_status"], {"qa_status": "vocab.batch_qa_status"})
        inst.add((u, GX.REL_01, ID["material/" + slug(r_["material_id"])]))
    for r_ in c.execute("select * from lab_results"):
        u = add_row("LabResult", r_["result_id"], r_, ["analyte", "result_value", "unit", "test_status", "measured_at"], {"test_status": "vocab.lab_test_status"})
        inst.add((u, GX.REL_02, ID["batch/" + slug(r_["batch_id"])]))
    for r_ in c.execute("select * from deviations"):
        u = add_row("Deviation", r_["deviation_id"], r_, ["opened_at", "classification", "root_cause", "status"],
                    {"status": "vocab.deviation_status", "classification": "vocab.deviation_classification", "root_cause": "vocab.quality_fault"})
        inst.add((u, GX.REL_03, ID["batch/" + slug(r_["batch_id"])]))
    for r_ in c.execute("select * from capa_actions"):
        u = add_row("CAPA", r_["capa_id"], r_, ["action_owner", "due_at", "state"], {"state": "vocab.capa_state"})
        inst.add((u, GX.REL_04, ID["deviation/" + slug(r_["deviation_id"])]))
    for r_ in c.execute("select * from cases"):
        add_row("Case", r_["id"], r_, ["account_id", "segment", "site", "region", "created_at", "status", "severity", "amount", "version"],
                {"status": "vocab.case_status", "segment": "vocab.case_segment", "site": "vocab.site", "region": "vocab.region", "severity": "vocab.severity"})
    for r_ in c.execute("select * from upstream_outages"):
        u = ID["upstreamoutage/" + slug(r_["incident_id"])]
        inst.add((u, RDF.type, GX.UpstreamOutage)); inst.add((u, RDFS.label, Literal(r_["incident_id"])))
        inst.add((u, GX.UpstreamOutage_system_name if False else GX.systemName, Literal(r_["system_name"])))
        inst_count["UpstreamOutage"] = inst_count.get("UpstreamOutage", 0) + 1
    inst.add((GX.systemName, RDF.type, OWL.DatatypeProperty))
    # NOTE: no Case->Batch/Deviation/CAPA links are written: GAP-REL-2 says they cannot be derived (human decision only).
    inst.serialize(OUT / "gxp-instances.ttl", format="turtle")
    print("instances:", inst_count, "triples:", len(inst))
model["instances"] = inst_count
model["counts"] = {"classes": len(ent["items"]), "relations": len(rel["items"]), "vocabs": len(tax["taxonomies"]),
                   "concepts": sum(len(t["values"]) for t in tax["taxonomies"]), "metrics": len(met["items"]),
                   "rules": len(br["items"]), "roles": len(acc["roles"]), "zoneh": len(model["zoneh"]), "workflows": len(wf["workflows"])}
json.dump(model, open(OUT / "ontology.json", "w"), indent=1)
print(model["counts"])
