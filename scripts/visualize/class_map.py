#!/usr/bin/env python3
"""Which kinds of measurement each pilot has: shared classes in the middle, pilots around them.

    neo4j-venv/bin/python scripts/visualize/class_map.py

Writes output/visualizations/class_map.html. The class hierarchy (eg:Measurement -> TemperatureMeasurement,
...) is drawn in grey; a coloured link from a pilot to a class means that pilot has variables of that
class, and its width/label is how many. Also prints the same matrix in the terminal.
"""
from collections import defaultdict

from pyvis.network import Network

from _common import (EG, PILOT_COLORS, GREY, bold, class_color, dim, output_path, parser, pilot_key, run)

USAGE = """
MATCH (p:Pilot)-[:mp__hasDataset]->(:Dataset)-[:eg__hasVariable]->(v)-[:INSTANCE_OF]->(c:OntologyClass)
RETURN p.displayName AS pilot, c.uri AS uri, c.displayName AS label, c.localName AS name, count(DISTINCT v) AS n
"""
HIERARCHY = """
MATCH (sub:OntologyClass)-[:rdfs__subClassOf]->(sup:OntologyClass)
WHERE sup.uri = $measurement OR (sup)-[:rdfs__subClassOf*1..3]->(:OntologyClass {uri: $measurement})
RETURN sub.uri AS sub, sub.displayName AS sub_label, sub.localName AS sub_name,
       sup.uri AS sup, sup.displayName AS sup_label
"""


def main():
    a = parser("Map of measurement classes per pilot").parse_args()
    usage = run(a, USAGE)
    hierarchy = run(a, HIERARCHY, measurement=EG + "Measurement")

    net = Network(height="900px", width="100%", directed=False, cdn_resources="in_line",
                  heading="EnergyGuard ontology · measurement classes per pilot")
    net.set_options("""{
      "physics": {"solver": "forceAtlas2Based",
                  "forceAtlas2Based": {"gravitationalConstant": -120, "springLength": 140},
                  "stabilization": {"iterations": 400}},
      "interaction": {"hover": true, "navigationButtons": true}
    }""")
    net.add_node(EG + "Measurement", label="Measurement", shape="ellipse", color="#37474F",
                 font={"color": "#FFFFFF", "size": 22}, title="eg:Measurement (all measured quantities)")
    totals = defaultdict(int)
    for u in usage:
        totals[u["uri"]] += u["n"]
    classes = {}
    for h in hierarchy:
        classes[h["sub"]] = (h["sub_label"], h["sub_name"])
        classes.setdefault(h["sup"], (h["sup_label"], h["sup"].split("#")[-1]))
    for u in usage:
        classes.setdefault(u["uri"], (u["label"], u["name"]))
    for uri, (label, name) in classes.items():
        if uri == EG + "Measurement":
            continue
        shared = uri.startswith(EG)
        net.add_node(uri, label=(label or name).replace(" Measurement", "").replace("Measurement", ""), shape="ellipse",
                     color=class_color(name), size=12 + min(totals.get(uri, 0), 120) / 6,
                     title=f"{'eg:' if shared else uri.split('/ontology/')[-1].split('#')[0] + ':'}{name}\n"
                           f"{totals.get(uri, 0)} variables")
    for h in hierarchy:
        net.add_edge(h["sub"], h["sup"], color="#B0BEC5", width=1, dashes=True)
    for pilot in sorted({u["pilot"] for u in usage}):
        key = pilot_key(pilot)
        net.add_node("pilot:" + key, label=key, shape="box", color=PILOT_COLORS.get(key, GREY),
                     font={"color": "#FFFFFF", "size": 20}, title=pilot)
    for u in usage:
        key = pilot_key(u["pilot"])
        net.add_edge("pilot:" + key, u["uri"], value=u["n"], label=str(u["n"]),
                     color=PILOT_COLORS.get(key, GREY), title=f"{key}: {u['n']} {u['label']}")

    path = output_path("class_map.html")
    net.write_html(str(path), notebook=False)

    # terminal matrix
    pilots = sorted({pilot_key(u["pilot"]) for u in usage})
    grid = defaultdict(dict)
    for u in usage:
        grid[(u["label"] or u["name"]).replace(" Measurement", "").replace("Measurement", "")][pilot_key(u["pilot"])] = u["n"]
    print(bold(f"{'class':22}" + "".join(f"{p:>9}" for p in pilots) + f"{'total':>9}"))
    for cls in sorted(grid, key=lambda c: -sum(grid[c].values())):
        row = grid[cls]
        print(f"{cls[:22]:22}" + "".join(f"{row.get(p, ''):>9}" if row.get(p) else dim(f"{'·':>9}") for p in pilots)
              + bold(f"{sum(row.values()):>9}"))
    print(f"\n-> {path.relative_to(path.parents[1])}")


if __name__ == "__main__":
    main()
