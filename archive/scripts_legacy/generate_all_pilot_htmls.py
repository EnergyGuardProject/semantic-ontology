#!/usr/bin/env python3

# Usage examples (from project root):
# 1) Fluid layout only:
# /home/energyguard/neo4j/neo4j-venv/bin/python \
#   /home/energyguard/neo4j/neo4j_saved_queries/all_pilots/generate_all_pilot_htmls.py \
#   --layout fluid
#
# 2) Hierarchical layout only:
# /home/energyguard/neo4j/neo4j-venv/bin/python \
#   /home/energyguard/neo4j/neo4j_saved_queries/all_pilots/generate_all_pilot_htmls.py \
#   --layout hierarchical
#
# 3) Both layouts:
# /home/energyguard/neo4j/neo4j-venv/bin/python \
#   /home/energyguard/neo4j/neo4j_saved_queries/all_pilots/generate_all_pilot_htmls.py \
#   --layout both

import argparse
from pathlib import Path

from py2neo import Graph
from pyvis.network import Network


# pilot labels set by 02_map_all_pilots_all_in_one.cypher, with their colours
PILOT_COLORS = {
    "RDN": "#EF5350",
    "CIEMAT": "#42A5F5",
    "BER": "#66BB6A",
    "CEA": "#26A69A",
    "CARTIF": "#9CCC65",
    "REA": "#FFA726",
    "ENGREEN": "#AB47BC",
}
PILOTS = list(PILOT_COLORS)
DEFAULT_LIMIT = 500


def parse_args():
    parser = argparse.ArgumentParser(description="Generate per-pilot HTML graph views")
    parser.add_argument(
        "--layout",
        choices=["fluid", "hierarchical", "both"],
        default="fluid",
        help="Graph layout mode for generated files",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="Max relationships per pilot to include",
    )
    return parser.parse_args()


def node_display_name(node):
    for key in ("displayName", "name", "localName", "eg__storedInDatabaseColumn", "uri"):
        if key in node:
            return str(node[key])
    return str(node.identity)


def pick_color(labels):
    for label in labels:
        if label in PILOT_COLORS:
            return PILOT_COLORS[label]
    return "#90A4AE"


def build_network(records, pilot, layout_mode):
    net = Network(height="900px", width="100%", directed=True)

    if layout_mode == "fluid":
        net.set_options(
            """
            {
              "interaction": {
                "hover": true,
                "navigationButtons": true,
                "keyboard": true
              },
              "physics": {
                "enabled": true,
                "solver": "forceAtlas2Based",
                "forceAtlas2Based": {
                  "gravitationalConstant": -35,
                  "centralGravity": 0.015,
                  "springLength": 110,
                  "springConstant": 0.08,
                  "damping": 0.45,
                  "avoidOverlap": 0.7
                },
                "stabilization": {
                  "enabled": true,
                  "iterations": 250
                }
              }
            }
            """
        )
    else:
        net.set_options(
            """
            {
              "interaction": {
                "hover": true,
                "navigationButtons": true,
                "keyboard": true
              },
              "layout": {
                "hierarchical": {
                  "enabled": true,
                  "direction": "UD",
                  "sortMethod": "hubsize"
                }
              },
              "physics": { "enabled": false }
            }
            """
        )

    for record in records:
        n = record["n"]
        m = record["m"]
        r = record["r"]

        n_id = str(n.identity)
        m_id = str(m.identity)

        n_labels = list(n.labels)
        m_labels = list(m.labels)

        n_label = node_display_name(n)
        m_label = node_display_name(m)

        net.add_node(
            n_id,
            label=n_label,
            title=f"{pilot} | " + ", ".join(n_labels),
            color=pick_color(n_labels),
        )
        net.add_node(
            m_id,
            label=m_label,
            title=f"{pilot} | " + ", ".join(m_labels),
            color=pick_color(m_labels),
        )

        rel_type = type(r).__name__
        net.add_edge(n_id, m_id, title=rel_type, label=rel_type)

    return net


def main():
    args = parse_args()

    graph = Graph(
        "bolt://127.0.0.1:7688",
        auth=("neo4j", "REDACTED"),
        name="neo4j",
    )

    base_dir = Path(__file__).resolve().parent
    out_dir = base_dir / "pilot htmls"
    out_dir.mkdir(parents=True, exist_ok=True)

    query = """
    MATCH (n)-[r]->(m)
    WHERE $pilot IN labels(n) OR $pilot IN labels(m)
    RETURN n, r, m
    LIMIT $limit
    """

    layout_modes = ["fluid", "hierarchical"] if args.layout == "both" else [args.layout]


    for pilot in PILOTS:
        records = graph.run(query, pilot=pilot, limit=args.limit).data()
        for layout_mode in layout_modes:
            net = build_network(records, pilot, layout_mode)
            out_file = out_dir / f"{pilot.lower()}_{layout_mode}.html"
            net.write_html(str(out_file), notebook=False)
            print(
                f"Generated {out_file} with {len(records)} relationships "
                f"(layout={layout_mode})"
            )


if __name__ == "__main__":
    main()
