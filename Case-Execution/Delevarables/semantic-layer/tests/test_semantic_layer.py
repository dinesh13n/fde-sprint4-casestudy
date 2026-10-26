"""Semantic layer tests (unittest only). Repo-backed tests skip if the repo is absent.
Run: python3 -m unittest discover -s tests -v     (env GXP_REPO overrides the repo root)"""
import glob, json, os, re, sys, unittest
import yaml
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.environ.get("GXP_REPO") or os.path.normpath(os.path.join(HERE, "..", "..", "..", "gxp-quality-hub-legacy"))
HAVE_REPO = os.path.isdir(os.path.join(REPO, "hub"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
FILES = ["entities","relationships","status-taxonomy","business-rules","metrics","access-semantics","ai-context-policy",
         "workflow-semantics","domain-constraints","context-dependencies","spec-business-rules","access-permission-matrix","error-catalogue"]

def Y(n):
    with open(os.path.join(ROOT, n + ".yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)

def walk(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k, v
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)

class Parse(unittest.TestCase):
    def test_all_yaml_parses(self):
        for n in FILES:
            self.assertIsInstance(Y(n), dict, n)
            self.assertEqual(Y(n)["semantic_layer_version"], "0.1.0", n)

class Ids(unittest.TestCase):
    def test_unique_ids(self):
        for n, key in [("entities","items"),("relationships","items"),("business-rules","items"),("metrics","items"),
                       ("spec-business-rules","items"),("status-taxonomy","taxonomies"),("domain-constraints","constraints")]:
            ids = [i["id"] for i in Y(n)[key]]
            self.assertEqual(len(ids), len(set(ids)), "duplicate ids in " + n)

    def test_evidence_and_status_present(self):
        for n in ["entities","relationships","business-rules"]:
            for i in Y(n)["items"]:
                self.assertTrue(i.get("evidence"), "%s %s has no evidence" % (n, i["id"]))
                self.assertIn(i.get("epistemic_status"), ["verified_fact","inference","assumption","unknown"], i["id"])

class Integrity(unittest.TestCase):
    def setUp(self):
        self.ents = {i["id"] for i in Y("entities")["items"]}
        self.vocabs = {i["id"] for i in Y("status-taxonomy")["taxonomies"]}

    def test_relationship_endpoints(self):
        for r in Y("relationships")["items"]:
            for end in (r["from"], r["to"]):
                self.assertIn(end, self.ents, "%s -> unknown entity %s" % (r["id"], end))

    def test_rule_applies_to(self):
        for r in Y("business-rules")["items"]:
            for e in r.get("applies_to", []):
                self.assertIn(e, self.ents, "%s applies_to unknown %s" % (r["id"], e))

    def test_vocab_refs_resolve(self):
        for n in FILES:
            for k, v in walk(Y(n)):
                vals = v if isinstance(v, list) else [v]
                for x in vals:
                    if isinstance(x, str) and re.fullmatch(r"vocab\.[a-z_]+", x) and k != "id":
                        self.assertIn(x, self.vocabs, "%s: unresolved %s" % (n, x))

    def test_open_decisions_resolve(self):
        defined = {d["id"] for d in Y("context-dependencies")["open_decisions"]}
        for n in FILES:
            for k, v in walk(Y(n)):
                if k == "open_decision" and isinstance(v, str):
                    self.assertIn(v, defined, "undefined open_decision %s in %s" % (v, n))

    def test_glossary_covers_entities(self):
        terms = {t["term"] for t in __import__("build_json").glossary()}
        self.assertFalse(self.ents - terms, "missing glossary terms: %s" % sorted(self.ents - terms))

class Invariants(unittest.TestCase):
    def test_zone_h_ten_and_no_holders(self):
        a = Y("access-semantics")["zone_h"]
        self.assertEqual(len(a["actions"]), 10)
        self.assertEqual(a["holders"], [])
        zh = [t for t in Y("status-taxonomy")["taxonomies"] if t["id"] == "vocab.zone_h_action"][0]
        self.assertEqual(len(zh["values"]), 10)

    def test_closed_in_four_vocabularies(self):
        n = 0
        for t in Y("status-taxonomy")["taxonomies"]:
            vals = json.dumps(t.get("values", []))
            if re.search(r'"CLOSED"', vals):
                n += 1
        self.assertGreaterEqual(n, 4)
        self.assertEqual(Y("status-taxonomy")["cross_vocabulary_mapping"]["policy"], "forbidden_unless_adopted_policy")

    def test_no_ai(self):
        self.assertEqual(Y("ai-context-policy")["decision"]["id"], "OD-08")
        inv = {m["name"]: m["required_value"] for m in Y("metrics")["items"] if m["kind"] == "invariant_metric"}
        self.assertEqual(inv["model_calls_total"], 0)

    def test_metric_split_never_chooses_winner(self):
        ids = {m["id"] for m in Y("metrics")["items"]}
        for base in ("K-04", "K-09"):
            for tag in ("OPS", "EVID", "FIN"):
                self.assertIn("%s-%s" % (base, tag), ids)

    def test_synthetic_label(self):
        self.assertIn("synthetic", Y("metrics")["global_conventions"]["label"])

class Generated(unittest.TestCase):
    def test_json_valid_and_in_sync(self):
        import jsonschema, build_json
        p = os.path.join(ROOT, "generated", "semantic-layer.json")
        if not os.path.exists(p):
            self.skipTest("generated JSON missing: run tools/build_json.py")
        got = json.load(open(p, encoding="utf-8"))
        schema = json.load(open(os.path.join(ROOT, "schemas", "semantic-layer.schema.json")))
        jsonschema.validate(got, schema)
        want = json.loads(json.dumps(build_json.build(), sort_keys=True, default=str))
        self.assertEqual(got, want, "generated JSON out of date: run tools/build_json.py")

@unittest.skipUnless(HAVE_REPO, "repo not found at %s" % REPO)
class RepoBacked(unittest.TestCase):
    def test_evidence_paths_exist(self):
        bad = set()
        for n in FILES:
            for k, v in walk(Y(n)):
                if k == "evidence" and isinstance(v, list):
                    for p in v:
                        if isinstance(p, str) and "/" in p and not p.startswith("semantic-layer") and not os.path.exists(os.path.join(REPO, p)):
                            bad.add(p)
        self.assertFalse(bad, "missing evidence paths: %s" % sorted(bad))

    def test_routes_48_and_roles(self):
        reg = json.load(open(os.path.join(REPO, "hub/security/route_registry.json")))
        self.assertEqual(len(reg["routes"]), 48)
        self.assertEqual(len(Y("access-permission-matrix")["routes"]), 48)
        roles = {r for x in reg["routes"] for r in x["roles"]} - {"public"}
        self.assertEqual(roles, {r["id"] for r in Y("access-semantics")["roles"]})

    def test_sbr_count(self):
        n = len(re.findall(r"^\|\s*SBR-", open(os.path.join(REPO, "docs/12-specs/business-rules.md"), encoding="utf-8").read(), re.M))
        self.assertEqual(n, len(Y("spec-business-rules")["items"]))
        self.assertEqual(n, 48)

if __name__ == "__main__":
    unittest.main()
