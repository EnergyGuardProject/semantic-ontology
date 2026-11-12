#!/usr/bin/env python3
"""Generate every visualisation and an index page.

    neo4j-venv/bin/python scripts/visualize/make_all.py

Writes into output/visualizations/: index.html, structure.html, pilot_map.html, query_demo.txt,
pilot_<name>.html (one per pilot), class_map.html, lake_coverage.html, structure.graphml, overview.txt.
"""
import os
import subprocess
import sys
from pathlib import Path

from _common import OUT_DIR, parser, pilot_key, run

HERE = Path(__file__).resolve().parent


def step(script, *args, env, capture=None):
    cmd = [sys.executable, str(HERE / script), *args]
    print("$", " ".join([script, *args]))
    if capture:
        out = subprocess.run(cmd, check=True, capture_output=True, text=True, env={**env, "NO_COLOR": "1"}).stdout
        capture.write_text(out, encoding="utf-8")
    else:
        subprocess.run(cmd, check=True, env=env)


def main():
    a = parser("Generate all visualisations").parse_args()
    # connection goes through the environment, so the password is neither printed nor visible in `ps`
    env = {**os.environ, "NEO4J_URI": a.uri, "NEO4J_USER": a.user, "NEO4J_PASSWORD": a.password}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    step("structure.py", env=env)
    step("pilot_map.py", env=env)
    step("query_demo.py", env=env, capture=OUT_DIR / "query_demo.txt")
    step("overview.py", env=env, capture=OUT_DIR / "overview.txt")
    step("pilot_graph.py", "--all", env=env)
    step("class_map.py", env=env)
    step("lake_coverage.py", "--html", env=env)
    step("export_graphml.py", env=env)

    pilots = [pilot_key(r["pilot"]) for r in run(a, "MATCH (p:Pilot) RETURN p.displayName AS pilot ORDER BY pilot")]
    links = "".join(f'<li><a href="pilot_{p.lower()}.html">{p}</a></li>' for p in pilots)
    (OUT_DIR / "index.html").write_text(f"""<!doctype html><html><head><meta charset="utf-8">
<title>EnergyGuard ontology</title>
<style>body{{font-family:system-ui,sans-serif;margin:40px;color:#263238;max-width:820px}}
a{{color:#1565C0}} li{{margin:6px 0}} code{{background:#ECEFF1;padding:2px 5px;border-radius:3px}}</style></head>
<body><h1>EnergyGuard ontology</h1>
<h2>Structure</h2><ul>
<li><a href="structure.html">The shape of the graph</a>: kinds of nodes and how they connect, with counts</li>
<li><a href="pilot_map.html">What is in it</a>: pilots → datasets → kinds of measurement, on one page</li>
<li><a href="class_map.html">Measurement classes per pilot</a></li>
<li><a href="query_demo.txt">How to use it</a>: everyday questions, the Cypher query and the answer</li></ul>
<h2>Data lake</h2><ul>
<li><a href="lake_coverage.html">Coverage</a>: how much of each pilot's metadata is in the lake</li>
<li><a href="overview.txt">Datasets and their location</a> (text)</li>
<li><a href="structure.graphml">structure.graphml</a>: for Gephi / yEd</li></ul>
<h2>Pilots in detail</h2><p>pilot → datasets → every variable, coloured by measurement class</p><ul>{links}</ul>
</body></html>""", encoding="utf-8")
    print(f"\nopen {OUT_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
