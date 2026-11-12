#!/usr/bin/env python3
"""A readable map of what is in the graph: pilots -> datasets -> kinds of measurement.

    neo4j-venv/bin/python scripts/visualize/pilot_map.py               # all pilots on one page
    neo4j-venv/bin/python scripts/visualize/pilot_map.py --pilot CEA   # one pilot

Variables are grouped by what they measure ("Temperature ×19", "Pressure ×8", ...) instead of drawn one
by one, so the whole ontology fits on one page. Prints the same as an outline in the terminal and writes
output/visualizations/pilot_map[_<pilot>].html. Hover a bucket to see the variable names in it.
"""
from collections import defaultdict

from pyvis.network import Network

from _common import (GREY, PILOT_COLORS, bold, class_color, class_key, dim, output_path, parser, pilot_key, run)

QUERY = """
MATCH (p:Pilot)-[:mp__hasDataset]->(d:Dataset)
WHERE $pilot IS NULL OR p.displayName STARTS WITH $pilot
OPTIONAL MATCH (d)-[:eg__hasVariable]->(v)
WITH p, d, v,
     // time-series signals without a class -> 'Other'; columns of static/GIS tables -> 'Attributes'
     CASE WHEN v IS NULL THEN NULL
          WHEN v.measurementType IS NOT NULL THEN v.measurementType
          WHEN toLower(coalesce(d.eg__datasetType[0], '')) CONTAINS 'time series' OR d.eg__tableLayout[0] = 'long' THEN 'Other'
          ELSE 'Attributes' END AS kind
RETURN p.displayName AS pilot, d.uri AS d_uri, d.displayName AS dataset,
       d.eg__datasetType[0] AS dtype, kind, count(v) AS n, collect(v.displayName)[0..25] AS names
ORDER BY pilot, dataset, n DESC
"""


def main():
    p = parser("Pilots -> datasets -> kinds of measurement")
    p.add_argument("--pilot", help="only this pilot (e.g. CEA, BER, REA)")
    a = p.parse_args()
    rows = run(a, QUERY, pilot=a.pilot.upper() if a.pilot else None)
    if not rows:
        p.error(f"no datasets for pilot {a.pilot}")

    tree = defaultdict(lambda: defaultdict(list))
    meta = {}
    for r in rows:
        tree[r["pilot"]][r["d_uri"]].append(r)
        meta[r["d_uri"]] = (r["dataset"], r["dtype"])

    # ---------- terminal outline ----------
    title = pilot_key(rows[0]["pilot"]) if a.pilot else "all pilots"
    print(bold(f"EnergyGuard ontology · what is in it · {title}"))
    for pilot in sorted(tree):
        nv = sum(r["n"] for ds in tree[pilot].values() for r in ds)
        nd = len(tree[pilot])
        print("\n" + bold(pilot_key(pilot)) + dim(f"  {nd} dataset{'s' if nd != 1 else ''} · {nv} variables"))
        for d_uri, buckets in sorted(tree[pilot].items(), key=lambda x: meta[x[0]][0]):
            name, dtype = meta[d_uri]
            kinds = [f"{class_key(b['kind']) or 'Other'} ×{b['n']}" for b in buckets if b["kind"]]
            print(f"  • {name[:60]}" + dim(f"  ({dtype})" if dtype else ""))
            print("      " + (", ".join(kinds) if kinds else dim("no variables described yet")))

    # ---------- HTML map ----------
    net = Network(height="920px", width="100%", directed=True, cdn_resources="in_line",
                  heading=f"EnergyGuard ontology · pilots → datasets → kinds of measurement · {title}")
    net.set_options("""{
      "layout": {"hierarchical": {"enabled": true, "direction": "LR", "sortMethod": "directed",
                                  "levelSeparation": 330, "nodeSpacing": 26, "treeSpacing": 60}},
      "physics": {"enabled": false},
      "interaction": {"hover": true, "navigationButtons": true, "keyboard": true},
      "edges": {"color": {"color": "#CFD8DC"}, "smooth": {"type": "cubicBezier", "forceDirection": "horizontal"}}
    }""")
    if not a.pilot:
        net.add_node("root", label="EnergyGuard\npilots", shape="box", color="#263238", level=0,
                     font={"color": "#FFFFFF", "size": 22}, margin=12)
    for pilot in sorted(tree):
        key = pilot_key(pilot)
        colour = PILOT_COLORS.get(key, GREY)
        nv = sum(r["n"] for ds in tree[pilot].values() for r in ds)
        nd = len(tree[pilot])
        net.add_node("p:" + key, label=f"{key}\n{nd} dataset{'s' if nd != 1 else ''} · {nv} variables", shape="box",
                     color=colour, level=1, margin=10, font={"color": "#FFFFFF", "size": 20}, title=pilot)
        if not a.pilot:
            net.add_edge("root", "p:" + key)
        for d_uri, buckets in tree[pilot].items():
            name, dtype = meta[d_uri]
            nd = sum(b["n"] for b in buckets)
            net.add_node(d_uri, label=f"{name[:42]}\n{nd} variables", shape="box", level=2, margin=8,
                         color={"background": "#FAFAFA", "border": colour}, borderWidth=2,
                         title=f"{name}\n{dtype or ''}")
            net.add_edge("p:" + key, d_uri, color=colour)
            for b in buckets:
                if not b["kind"]:
                    continue
                bid = f"{d_uri}|{b['kind']}"
                label = class_key(b["kind"]) or "Other"
                names = ", ".join(b["names"]) + (" …" if b["n"] > len(b["names"]) else "")
                net.add_node(bid, label=f"{label} ×{b['n']}", shape="dot", level=3,
                             size=8 + min(b["n"], 150) ** 0.6 * 2, color=class_color(b["kind"]),
                             title=f"{label}: {b['n']} variables\n{names}")
                net.add_edge(d_uri, bid, color="#CFD8DC")
    path = output_path(f"pilot_map{'_' + title.lower() if a.pilot else ''}.html")
    net.write_html(str(path), notebook=False)
    print(f"\n-> {path.relative_to(path.parents[1])}")


if __name__ == "__main__":
    main()
