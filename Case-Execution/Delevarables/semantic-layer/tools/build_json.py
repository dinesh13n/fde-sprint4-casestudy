#!/usr/bin/env python3
"""Compile all YAML + glossary into generated/semantic-layer.json (the serving artifact)."""
import json, os, re
import yaml
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ["entities","relationships","status-taxonomy","business-rules","metrics","access-semantics","ai-context-policy",
         "workflow-semantics","domain-constraints","context-dependencies","spec-business-rules","access-permission-matrix","error-catalogue"]

def load(n):
    with open(os.path.join(OUT, n + ".yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)

def glossary():
    rows = []
    for line in open(os.path.join(OUT, "glossary.md"), encoding="utf-8"):
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) == 3 and c[0] not in ("Term", "---") and not set(c[0]) <= set("-"):
            rows.append({"term": c[0], "definition": c[1], "source": c[2]})
    return rows

def build():
    doc = {"semantic_layer_version": "0.1.0", "label": "synthetic, unvalidated"}
    for n in FILES:
        doc[n.replace("-", "_")] = load(n)
    doc["glossary"] = glossary()
    return doc

if __name__ == "__main__":
    os.makedirs(os.path.join(OUT, "generated"), exist_ok=True)
    p = os.path.join(OUT, "generated", "semantic-layer.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(build(), f, indent=1, sort_keys=True, ensure_ascii=False, default=str)
        f.write("\n")
    print("wrote", p)
