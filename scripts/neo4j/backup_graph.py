#!/usr/bin/env python3
"""Export a Neo4j graph to a JSON file (nodes, relationships, n10s config and prefixes).

A logical backup taken without stopping the database, meant for the small ontology graph.
Run before scripts/neo4j/reload_ontology.sh replaces a graph.

    neo4j-venv/bin/python scripts/neo4j/backup_graph.py                       # this project's instance (7689)
    neo4j-venv/bin/python scripts/neo4j/backup_graph.py --uri bolt://localhost:7687   # old live instance

Writes output/backups/<name>_<timestamp>.json. Environment: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD.
"""
import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser(description="Export a Neo4j graph to JSON")
    ap.add_argument("--uri", default=os.environ.get("NEO4J_URI", "bolt://localhost:7689"))
    ap.add_argument("--user", default=os.environ.get("NEO4J_USER", "neo4j"))
    ap.add_argument("--password", default=os.environ.get("NEO4J_PASSWORD", "REDACTED"))
    ap.add_argument("--name", default=None, help="file name prefix (default: from the port)")
    a = ap.parse_args()

    out_dir = ROOT / "output" / "backups"
    out_dir.mkdir(parents=True, exist_ok=True)
    name = a.name or ("neo4j-ontology" if a.uri.endswith(":7689") else "neo4j_" + a.uri.rsplit(":", 1)[-1])
    path = out_dir / f"{name}_{datetime.now():%Y%m%d_%H%M%S}.json"

    with GraphDatabase.driver(a.uri, auth=(a.user, a.password)) as driver:
        with driver.session() as s:
            nodes = s.run("MATCH (n) RETURN elementId(n) AS id, labels(n) AS labels, properties(n) AS props").data()
            rels = s.run("MATCH (a)-[r]->(b) RETURN elementId(a) AS start, elementId(b) AS end, "
                         "type(r) AS type, properties(r) AS props").data()
            try:
                config = s.run("CALL n10s.graphconfig.show()").data()
            except Exception:
                config = []
            try:
                prefixes = s.run("CALL n10s.nsprefixes.list()").data()
            except Exception:
                prefixes = []
            schema = s.run("SHOW CONSTRAINTS YIELD name, createStatement RETURN name, createStatement").data()

    path.write_text(json.dumps({"uri": a.uri, "taken": datetime.now().isoformat(), "nodes": nodes,
                                "relationships": rels, "n10s_config": config, "n10s_prefixes": prefixes,
                                "constraints": schema}, default=str, indent=1, ensure_ascii=False))
    print(f"{len(nodes)} nodes, {len(rels)} relationships -> {path}")


if __name__ == "__main__":
    main()
