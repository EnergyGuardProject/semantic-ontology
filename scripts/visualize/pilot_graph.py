#!/usr/bin/env python3
"""Interactive graph of a pilot: pilot -> datasets -> variables, coloured by measurement class.

    neo4j-venv/bin/python scripts/visualize/pilot_graph.py --pilot CEA
    neo4j-venv/bin/python scripts/visualize/pilot_graph.py --pilot BER --groups      # + sensor groups
    neo4j-venv/bin/python scripts/visualize/pilot_graph.py --all                     # one page per pilot
    neo4j-venv/bin/python scripts/visualize/pilot_graph.py --pilot REA --layout force

Writes output/visualizations/pilot_<name>.html (self-contained: open it in any browser).
Hover a node for its details. Variables found in the data lake have a solid border, the ones that
are not have a red dashed border.
"""
from pyvis.network import Network

from _common import (GREY, PILOT_COLORS, class_color, first, output_path, parser, pilot_key, run)

QUERY = """
MATCH (p:Pilot)-[:mp__hasDataset]->(d:Dataset)
WHERE p.displayName STARTS WITH $pilot
OPTIONAL MATCH (d)-[:eg__hasVariable]->(v)
RETURN p.displayName AS pilot, d.uri AS d_uri, d.displayName AS dataset,
       d.eg__storedInDatabase AS db, d.eg__storedInDatabaseTable AS tables, d.eg__tableLayout AS layout,
       d.dcterms__description AS d_desc,
       v.uri AS v_uri, v.displayName AS variable, v.measurementType AS class, v.eg__unit AS unit,
       v.dcterms__description AS v_desc, v.lakeMatch AS how,
       coalesce(v.lakeSensorId, v.lakeSensorPattern, v.lakeColumn) AS lake
"""
GROUPS = """
MATCH (p:Pilot)-[:mp__hasDataset]->(:Dataset)-[:eg__hasVariable]->(v)<-[:HAS_MEASUREMENT]-(g:MeasurementGroup)
WHERE p.displayName STARTS WITH $pilot
RETURN DISTINCT g.uri AS g_uri, g.displayName AS grp, v.uri AS v_uri
"""
PILOTS = "MATCH (p:Pilot) RETURN p.displayName AS pilot ORDER BY pilot"

OPTIONS_TREE = """{
  "layout": {"hierarchical": {"enabled": true, "direction": "LR", "sortMethod": "directed",
                              "levelSeparation": 260, "nodeSpacing": 18, "treeSpacing": 40}},
  "physics": {"enabled": false},
  "interaction": {"hover": true, "navigationButtons": true, "keyboard": true},
  "edges": {"color": {"color": "#CFD8DC"}, "smooth": {"type": "cubicBezier", "forceDirection": "horizontal"}}
}"""
OPTIONS_FORCE = """{
  "physics": {"solver": "forceAtlas2Based", "forceAtlas2Based": {"gravitationalConstant": -60, "springLength": 80},
              "stabilization": {"iterations": 300}},
  "interaction": {"hover": true, "navigationButtons": true, "keyboard": true},
  "edges": {"color": {"color": "#CFD8DC"}}
}"""


def text(*lines):
    return "\n".join(str(x) for x in lines if x)


def build(a, pilot):
    rows = run(a, QUERY, pilot=pilot)
    if not rows:
        print(f"no datasets for pilot '{pilot}'")
        return None
    name = pilot_key(rows[0]["pilot"])
    net = Network(height="900px", width="100%", directed=True, bgcolor="#FFFFFF", cdn_resources="in_line",
                  heading=f"EnergyGuard ontology · {rows[0]['pilot']}")
    net.set_options(OPTIONS_TREE if a.layout == "tree" else OPTIONS_FORCE)
    color = PILOT_COLORS.get(name, GREY)
    net.add_node("pilot", label=name, shape="box", color=color, font={"size": 28, "color": "#FFFFFF"},
                 title=f"Pilot {rows[0]['pilot']}", level=0)
    seen = set()
    for r in rows:
        if r["d_uri"] not in seen:
            seen.add(r["d_uri"])
            db = first(r["db"])
            tables = r["tables"] if isinstance(r["tables"], list) else [r["tables"]]
            where = f"{db} · {', '.join(t for t in tables if t)} [{first(r['layout'])}]" if db else "not in the data lake"
            net.add_node(r["d_uri"], label=r["dataset"][:45], shape="box", level=1,
                         color={"background": "#ECEFF1", "border": color}, borderWidth=2,
                         title=text(r["dataset"], f"data lake: {where}", (first(r["d_desc"]) or "")[:300]))
            net.add_edge("pilot", r["d_uri"])
        if r["v_uri"]:
            if r["v_uri"] not in seen:
                seen.add(r["v_uri"])
                how = first(r["how"]) or "none"
                in_lake = how != "none"
                net.add_node(r["v_uri"], label=r["variable"][:30], shape="dot", size=9, level=2,
                             color={"background": class_color(r["class"]), "border": "#455A64" if in_lake else "#D32F2F"},
                             borderWidth=1 if in_lake else 2, shapeProperties={"borderDashes": not in_lake},
                             title=text(r["variable"], (r["class"] or "no measurement class"),
                                        f"unit: {first(r['unit'])}" if first(r["unit"]) else "",
                                        (first(r["v_desc"]) or "")[:200],
                                        f"lake: {first(r['lake'])} ({how})" if first(r["lake"]) else "not found in the data lake"))
            net.add_edge(r["d_uri"], r["v_uri"])
    if a.groups:
        for g in run(a, GROUPS, pilot=pilot):
            if g["g_uri"] not in seen:
                seen.add(g["g_uri"])
                net.add_node(g["g_uri"], label=g["grp"], shape="diamond", size=14, color="#90A4AE", level=3,
                             title=f"sensor group {g['grp']}")
            net.add_edge(g["g_uri"], g["v_uri"], color="#FFB74D", dashes=True)
    path = output_path(f"pilot_{name.lower()}.html")
    net.write_html(str(path), notebook=False)
    n_vars = sum(1 for n in net.nodes if n.get("level") == 2)
    print(f"{name:8} {len(seen) - n_vars:3} datasets/groups · {n_vars:4} variables -> {path.relative_to(path.parents[1])}")
    return path


def main():
    p = parser("Interactive HTML graph of a pilot's datasets and variables")
    p.add_argument("--pilot", help="pilot name, e.g. CEA, BER, REA, ENGREEN")
    p.add_argument("--all", action="store_true", help="one page per pilot")
    p.add_argument("--groups", action="store_true", help="also show sensor groups (orange dashed links)")
    p.add_argument("--layout", choices=["tree", "force"], default="tree")
    a = p.parse_args()
    if not a.pilot and not a.all:
        p.error("give --pilot NAME or --all")
    pilots = [r["pilot"] for r in run(a, PILOTS)] if a.all else [a.pilot.upper()]
    for pilot in pilots:
        build(a, pilot_key(pilot))


if __name__ == "__main__":
    main()
