#!/usr/bin/env python3
"""Export one pilot subgraph from Neo4j to GraphML for external visualization tools.

Usage:
  python scripts/export_pilot_graphml.py \
    --uri bolt://localhost:7688 \
    --user neo4j \
    --password 'neo4j@energyguard' \
    --pilot Pilot3 \
    --output /home/energyguard/neo4j/import/pilot3.graphml \
    --limit 5000
"""

from __future__ import annotations

import argparse
from typing import Any


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Export pilot subgraph to GraphML")
    p.add_argument("--uri", required=True, help="Neo4j Bolt URI, e.g. bolt://localhost:7688")
    p.add_argument("--user", required=True, help="Neo4j username")
    p.add_argument("--password", required=True, help="Neo4j password")
    p.add_argument("--pilot", required=True, help="Pilot label: Pilot1..Pilot5")
    p.add_argument("--output", required=True, help="Output GraphML file path")
    p.add_argument("--limit", type=int, default=5000, help="Max relationships to export")
    return p


def _to_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return "|".join(str(v) for v in value)
    return str(value)


def main() -> int:
    args = build_parser().parse_args()

    try:
        from neo4j import GraphDatabase
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            "Missing dependency: neo4j. Install with: pip install neo4j networkx"
        ) from exc

    try:
        import networkx as nx
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            "Missing dependency: networkx. Install with: pip install neo4j networkx"
        ) from exc

    query = """
    MATCH (n)-[r]->(m)
    WHERE $pilot IN labels(n) OR $pilot IN labels(m)
    RETURN
      id(n) AS n_id,
      labels(n) AS n_labels,
      properties(n) AS n_props,
      id(m) AS m_id,
      labels(m) AS m_labels,
      properties(m) AS m_props,
      type(r) AS r_type,
      properties(r) AS r_props
    LIMIT $limit
    """

    graph = nx.MultiDiGraph()

    driver = GraphDatabase.driver(args.uri, auth=(args.user, args.password))
    try:
        with driver.session() as session:
            result = session.run(query, pilot=args.pilot, limit=args.limit)
            row_count = 0
            for row in result:
                row_count += 1
                n_id = str(row["n_id"])
                m_id = str(row["m_id"])

                n_props = row["n_props"] or {}
                m_props = row["m_props"] or {}
                r_props = row["r_props"] or {}

                n_attrs = {
                    "labels": _to_str(row["n_labels"]),
                    "name": _to_str(
                        n_props.get("displayName")
                        or n_props.get("localName")
                        or n_props.get("uri")
                        or n_id
                    ),
                }
                for k, v in n_props.items():
                    n_attrs[f"p_{k}"] = _to_str(v)

                m_attrs = {
                    "labels": _to_str(row["m_labels"]),
                    "name": _to_str(
                        m_props.get("displayName")
                        or m_props.get("localName")
                        or m_props.get("uri")
                        or m_id
                    ),
                }
                for k, v in m_props.items():
                    m_attrs[f"p_{k}"] = _to_str(v)

                graph.add_node(n_id, **n_attrs)
                graph.add_node(m_id, **m_attrs)

                edge_attrs = {"type": _to_str(row["r_type"])}
                for k, v in r_props.items():
                    edge_attrs[f"p_{k}"] = _to_str(v)

                graph.add_edge(n_id, m_id, **edge_attrs)

        nx.write_graphml(graph, args.output)
        print(
            f"Exported {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges "
            f"to {args.output}"
        )
        if row_count == 0:
            print("No rows returned. Check pilot label and database content.")
    finally:
        driver.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
