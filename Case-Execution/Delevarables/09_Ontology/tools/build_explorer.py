#!/usr/bin/env python3
"""Embed ontology.json + sparql_results.md into one offline HTML page (ontology_explorer.html)."""
import json, html
from pathlib import Path
H = Path(__file__).resolve().parent.parent
m = json.load(open(H/"ontology.json"))
sp = (H/"sparql_results.md").read_text(encoding="utf-8").split("\n## ")[1:]
m["sparql"] = [{"title": s.split("\n",1)[0], "body": s.split("\n",1)[1]} for s in sp]
page = open(Path(__file__).with_name("explorer_template.html"), encoding="utf-8").read()
page = page.replace("/*DATA*/null", json.dumps(m).replace("</", "<\\/"))
(H/"ontology_explorer.html").write_text(page, encoding="utf-8")
print("ok", len(page))
