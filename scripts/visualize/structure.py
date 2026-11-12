#!/usr/bin/env python3
"""The shape of the graph: which kinds of nodes exist and how they connect, with counts.

    neo4j-venv/bin/python scripts/visualize/structure.py               # whole graph
    neo4j-venv/bin/python scripts/visualize/structure.py --pilot BER   # one pilot

Prints a diagram in the terminal and writes output/visualizations/structure[_<pilot>].html, where every box
is a kind of node (Pilot, Dataset, Variable, ...) and every arrow a relationship, each with how many
there are. Hover a box to see what it holds and example names.
"""
from pyvis.network import Network

from _common import bold, cyan, dim, output_path, parser, pilot_key, run

# Every pattern is restricted to the chosen pilot (or none) through its datasets.
SCOPE = """
MATCH (p:Pilot)-[:mp__hasDataset]->(d:Dataset)
WHERE $pilot IS NULL OR p.displayName STARTS WITH $pilot
"""
COUNTS = {
    "pilots": SCOPE + "RETURN count(DISTINCT p) AS n, collect(DISTINCT p.displayName)[0..7] AS ex",
    "datasets": SCOPE + "RETURN count(DISTINCT d) AS n, collect(DISTINCT d.displayName)[0..6] AS ex",
    "variables": SCOPE + "MATCH (d)-[:eg__hasVariable]->(v) "
                         "RETURN count(DISTINCT v) AS n, collect(DISTINCT v.displayName)[0..8] AS ex",
    "has_variable": SCOPE + "MATCH (d)-[r:eg__hasVariable]->() RETURN count(r) AS n, collect(null) AS ex",
    "classes": SCOPE + "MATCH (d)-[:eg__hasVariable]->(v)-[:INSTANCE_OF]->(c) "
                       "RETURN count(DISTINCT c) AS n, collect(DISTINCT c.displayName)[0..10] AS ex",
    "instance_of": SCOPE + "MATCH (d)-[:eg__hasVariable]->(v)-[r:INSTANCE_OF]->() RETURN count(DISTINCT v) AS n, collect(null) AS ex",
    "units": SCOPE + "MATCH (d)-[:eg__hasVariable]->(v)-[:eg__hasUnit]->(u) "
                     "RETURN count(DISTINCT u) AS n, collect(DISTINCT u.localName)[0..10] AS ex",
    "has_unit": SCOPE + "MATCH (d)-[:eg__hasVariable]->(v)-[:eg__hasUnit]->() RETURN count(DISTINCT v) AS n, collect(null) AS ex",
    "groups": SCOPE + "MATCH (d)-[:eg__hasVariable]->(v)<-[:eg__hasMeasurement]-(g) "
                      "RETURN count(DISTINCT g) AS n, collect(DISTINCT g.displayName)[0..6] AS ex",
    "has_measurement": SCOPE + "MATCH (d)-[:eg__hasVariable]->(v)<-[r:eg__hasMeasurement]-() RETURN count(DISTINCT r) AS n, collect(null) AS ex",
    "components": SCOPE + "MATCH (d)-[:eg__hasVariable]->(v)-[:eg__representsComponent]->(c) "
                          "RETURN count(DISTINCT c) AS n, collect(DISTINCT c.localName)[0..6] AS ex",
    "represents": SCOPE + "MATCH (d)-[:eg__hasVariable]->(v)-[r:eg__representsComponent]->() RETURN count(DISTINCT r) AS n, collect(null) AS ex",
    "tables": SCOPE + "WITH d WHERE d.eg__storedInDatabase IS NOT NULL "
                      "UNWIND d.eg__storedInDatabaseTable AS t "
                      "RETURN count(DISTINCT d.eg__storedInDatabase[0] + '.' + t) AS n, "
                      "collect(DISTINCT d.eg__storedInDatabase[0] + '.' + t)[0..6] AS ex",
    "stored_in": SCOPE + "WITH d WHERE d.eg__storedInDatabase IS NOT NULL RETURN count(DISTINCT d) AS n, collect(null) AS ex",
    "subpilots": SCOPE + "MATCH (p)-[:mp__hasSubPilot]->(s) RETURN count(DISTINCT s) AS n, collect(DISTINCT s.displayName) AS ex",
}

# kind of node -> (label, colour, what it holds)
BOXES = {
    "root": ("Pilots", "#263238", "the root of the pilot tree"),
    "pilots": ("Pilot", "#37474F", "a pilot organisation (CEA, BER, REA, ...)"),
    "subpilots": ("Sub-pilot", "#607D8B", "part of a pilot (only RDN: faults, time series)"),
    "datasets": ("Dataset", "#FFB300", "one data source: title, description, location, period,\n"
                                       "time resolution, licence, contact, data-lake location"),
    "variables": ("Variable", "#1E88E5", "one signal / column: name, description, unit, valid range,\n"
                                         "data type, kind, subsystem, data-lake sensor id"),
    "classes": ("Measurement class", "#43A047", "what a variable measures (eg:TemperatureMeasurement, ...)"),
    "measurement": ("eg:Measurement", "#2E7D32", "the shared top class of all measurement classes"),
    "units": ("Unit (QUDT)", "#8E24AA", "standard unit of a variable (unit:DEG_C, unit:KiloW, ...)"),
    "groups": ("Sensor group", "#F4511E", "a bundle of sensors from the original pilot ontology"),
    "components": ("System component", "#6D4C41", "the equipment a sensor belongs to"),
    "tables": ("Data-lake table", "#00897B", "where the readings are: database.table in the data lake"),
}
# (from, to, relationship, count key)
ARROWS = [
    ("root", "pilots", "hasPilot", "pilots"),
    ("pilots", "subpilots", "hasSubPilot", "subpilots"),
    ("pilots", "datasets", "hasDataset", "datasets"),
    ("datasets", "variables", "hasVariable", "has_variable"),
    ("datasets", "tables", "storedInDatabase / Table", "stored_in"),
    ("variables", "classes", "type (INSTANCE_OF)", "instance_of"),
    ("classes", "measurement", "subClassOf", None),
    ("variables", "units", "hasUnit", "has_unit"),
    ("groups", "variables", "hasMeasurement", "has_measurement"),
    ("variables", "components", "representsComponent", "represents"),
]


def main():
    p = parser("The shape of the graph, with counts")
    p.add_argument("--pilot", help="only this pilot (e.g. BER, CEA, REA)")
    a = p.parse_args()
    pilot = a.pilot.upper() if a.pilot else None
    c = {k: run(a, q, pilot=pilot)[0] for k, q in COUNTS.items()}
    if c["datasets"]["n"] == 0:
        p.error(f"no datasets for pilot {a.pilot}")
    c["root"] = {"n": 1, "ex": []}
    c["measurement"] = {"n": 1, "ex": []}
    scope = pilot_key(c["pilots"]["ex"][0]) if pilot else "all pilots"

    # ---------- terminal diagram ----------
    n = {k: v["n"] for k, v in c.items()}
    box = lambda label, k=None: cyan(f"[{label}{f' ×{n[k]}' if k else ''}]")
    sub = dim(f"  ─hasSubPilot→ [Sub-pilot ×{n['subpilots']}]") if n["subpilots"] else ""
    print(bold(f"EnergyGuard ontology · structure · {scope}\n"))
    print(f"  {box('Pilots')} ─hasPilot→ {box('Pilot', 'pilots')}{sub}")
    print(f"        └─hasDataset ({n['datasets']})→ {box('Dataset', 'datasets')}"
          f" ─stored in ({n['stored_in']})→ {box('Data-lake table', 'tables')}")
    print(f"              └─hasVariable ({n['has_variable']})→ {box('Variable', 'variables')}")
    lines = [(f"type ({n['instance_of']})→ {box('Measurement class', 'classes')} ─subClassOf→ {box('eg:Measurement')}", n["instance_of"]),
             (f"hasUnit ({n['has_unit']})→ {box('Unit', 'units')}", n["has_unit"]),
             (f"representsComponent ({n['represents']})→ {box('System component', 'components')}", n["represents"]),
             (f"←hasMeasurement ({n['has_measurement']})─ {box('Sensor group', 'groups')}", n["has_measurement"])]
    lines = [text for text, count in lines if count]
    for i, text in enumerate(lines):
        print(f"                    {'└─' if i == len(lines) - 1 else '├─'}{text}")
    print(dim("\n  numbers on arrows = how many links; ×N = how many nodes of that kind"))
    for k in ("pilots", "datasets", "classes", "units"):
        if c[k]["ex"]:
            print(dim(f"  {BOXES[k][0]:18} e.g. ") + ", ".join(str(x) for x in c[k]["ex"][:8]))

    # ---------- HTML diagram ----------
    net = Network(height="760px", width="100%", directed=True, cdn_resources="in_line",
                  heading=f"EnergyGuard ontology · structure · {scope}")
    net.set_options("""{
      "layout": {"hierarchical": {"enabled": true, "direction": "LR", "sortMethod": "directed",
                                  "levelSeparation": 290, "nodeSpacing": 140}},
      "physics": {"enabled": false},
      "interaction": {"hover": true, "navigationButtons": true},
      "edges": {"font": {"size": 13, "align": "middle", "background": "white"},
                "color": {"color": "#90A4AE"}, "arrows": {"to": {"scaleFactor": 0.8}},
                "smooth": {"type": "cubicBezier", "forceDirection": "horizontal"}}
    }""")
    for k, (label, colour, what) in BOXES.items():
        if c[k]["n"] == 0:
            continue
        count = "" if k in ("root", "measurement") else f"\n×{c[k]['n']}"
        examples = ", ".join(str(x) for x in c[k]["ex"][:8])
        net.add_node(k, label=f"{label}{count}", shape="box", color=colour, margin=14,
                     font={"color": "#FFFFFF", "size": 18, "face": "system-ui"},
                     title=f"{label}\n{what}" + (f"\n\ne.g. {examples}" if examples else ""))
    for src, dst, rel, key in ARROWS:
        if c[src]["n"] and c[dst]["n"] and (key is None or c[key]["n"]):
            net.add_edge(src, dst, label=rel + (f"  ({c[key]['n']})" if key else ""),
                         width=1 + (min(c[key]["n"], 1000) / 250 if key else 0))
    name = f"structure{'_' + scope.lower() if pilot else ''}.html"
    path = output_path(name)
    net.write_html(str(path), notebook=False)
    print(f"\n-> {path.relative_to(path.parents[1])}")


if __name__ == "__main__":
    main()
