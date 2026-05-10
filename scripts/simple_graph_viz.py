#!/usr/bin/env python3

from pathlib import Path

from py2neo import Graph
from pyvis.network import Network

graph = Graph("bolt://energyguard.epu.ntua.gr:7687", auth=("neo4j", "neo4j@energyguard"), name="neo4j")

query = """
MATCH (n)-[r]->(m)
WHERE any(label IN labels(n) WHERE label STARTS WITH 'ns')
   OR any(label IN labels(m) WHERE label STARTS WITH 'ns')
RETURN n, r, m
LIMIT 300
"""

rows = graph.run(query).data()
print(f"Fetched {len(rows)} relationships")

net = Network(height="900px", width="100%", directed=True)
net.force_atlas_2based()

seen = set()
for row in rows:
    for node in (row["n"], row["m"]):
        node_id = node.identity
        if node_id in seen:
            continue

        label = node.get("name") or node.get("ns1__storedInDatabaseColumn") or node.get("uri") or str(node_id)
        node_labels = list(node.labels)
        color = "#B0BEC5"
        for ns, hex_color in (("ns3__", "#4FC3F7"), ("ns2__", "#81C784"), ("ns1__", "#FFCC80"), ("ns0__", "#E57373")):
            if any(lbl.startswith(ns) for lbl in node_labels):
                color = hex_color
                break

        net.add_node(node_id, label=label, title=", ".join(node_labels), color=color)
        seen.add(node_id)

    rel_name = type(row["r"]).__name__
    net.add_edge(row["n"].identity, row["m"].identity, title=rel_name, label=rel_name)

print(f"Added {len(seen)} nodes and {len(rows)} edges")


def choose_output_path(filename: str = "owl_visualization.html") -> Path:
    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir,
        Path.cwd(),
        Path.home() / "neo4j_visualizations",
    ]

    for directory in candidates:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            if directory.is_dir() and directory.exists():
                probe = directory / ".write_test"
                with open(probe, "w", encoding="utf-8") as fh:
                    fh.write("ok")
                probe.unlink(missing_ok=True)
                return directory / filename
        except OSError:
            continue

    raise PermissionError("No writable output directory found for visualization HTML")


output_file = choose_output_path()
net.write_html(str(output_file), notebook=False)
print(f"Generated: {output_file}")
