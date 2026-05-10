#!/usr/bin/env python3
"""Export pilot subgraph to both HTML (PyVis) and GraphML.

This script is intentionally separate from existing files.

Example:
  python scripts/export_pilot_tree.py \
    --uri bolt://127.0.0.1:7688 \
    --user neo4j \
    --password 'neo4j@energyguard' \
    --database neo4j \
    --pilot Pilot3 \
    --limit 800 \
    --html pilot3_tree.html \
    --graphml pilot3_tree.graphml \
    --hierarchical
"""

from __future__ import annotations

import argparse

import networkx as nx
from py2neo import Graph
from pyvis.network import Network


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a pilot subgraph to HTML + GraphML")
    parser.add_argument("--uri", default="bolt://127.0.0.1:7688")
    parser.add_argument("--user", default="neo4j")
    parser.add_argument("--password", default="neo4j@energyguard")
    parser.add_argument("--database", default="neo4j")
    parser.add_argument("--pilot", default="Pilot3", help="Pilot label (Pilot1..Pilot5)")
    parser.add_argument("--limit", type=int, default=800)
    parser.add_argument("--html", default="pilot_tree.html")
    parser.add_argument("--graphml", default="pilot_tree.graphml")
    parser.add_argument("--hierarchical", action="store_true")
    return parser.parse_args()


def node_display_name(node) -> str:
    for key in ("displayName", "name", "localName", "eg__storedInDatabaseColumn", "uri"):
        if key in node:
            return str(node[key])
    return str(node.identity)


def pilot_color(labels) -> str:
    labels_set = set(labels)
    if "Pilot1" in labels_set:
        return "#EF5350"
    if "Pilot2" in labels_set:
        return "#42A5F5"
    if "Pilot3" in labels_set:
        return "#66BB6A"
    if "Pilot4" in labels_set:
        return "#FFA726"
    if "Pilot5" in labels_set:
        return "#AB47BC"
    return "#90A4AE"


def main() -> int:
    args = parse_args()

    graph = Graph(args.uri, auth=(args.user, args.password), name=args.database)

    query = """
    MATCH (n)-[r]->(m)
    WHERE $pilot IN labels(n) OR $pilot IN labels(m)
    RETURN n, r, m
    LIMIT $limit
    """

    rows = graph.run(query, pilot=args.pilot, limit=args.limit).data()

    net = Network(height="900px", width="100%", directed=True)
    if args.hierarchical:
        net.set_options(
            """
            {
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
    else:
        net.force_atlas_2based()

    gml = nx.MultiDiGraph()

    for rec in rows:
        n = rec["n"]
        m = rec["m"]
        r = rec["r"]

        n_id = str(n.identity)
        m_id = str(m.identity)

        n_labels = list(n.labels)
        m_labels = list(m.labels)

        n_name = node_display_name(n)
        m_name = node_display_name(m)

        rel_type = type(r).__name__

        net.add_node(n_id, label=n_name, title=", ".join(n_labels), color=pilot_color(n_labels))
        net.add_node(m_id, label=m_name, title=", ".join(m_labels), color=pilot_color(m_labels))
        net.add_edge(n_id, m_id, label=rel_type, title=rel_type)

        gml.add_node(n_id, name=n_name, labels="|".join(n_labels))
        gml.add_node(m_id, name=m_name, labels="|".join(m_labels))
        gml.add_edge(n_id, m_id, type=rel_type)

    net.write_html(args.html, notebook=False)
    nx.write_graphml(gml, args.graphml)

    print(f"Exported rows: {len(rows)}")
    print(f"HTML: {args.html}")
    print(f"GraphML: {args.graphml}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
