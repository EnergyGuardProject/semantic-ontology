#!/usr/bin/env python3
"""
Visualize OWL ontology imported into Neo4j using PyVis
"""
from py2neo import Graph
from pyvis.network import Network

# -----------------------------------------------------------
# 1) Connect to Neo4j
# -----------------------------------------------------------
graph = Graph(
    "bolt://energyguard.epu.ntua.gr:7687",  # Use the advertised hostname
    auth=("neo4j", "neo4j@energyguard"),
    name="neo4j"  # Change to your database name
)

# -----------------------------------------------------------
# 2) Run query to fetch ontology relationships
# -----------------------------------------------------------
query = """
MATCH (n)-[r]->(m)
WHERE any(label IN labels(n) WHERE label STARTS WITH 'ns') 
   OR any(label IN labels(m) WHERE label STARTS WITH 'ns')
RETURN n, r, m
LIMIT 300
"""

try:
    data = graph.run(query).data()
    print(f"Fetched {len(data)} relationships")
except Exception as e:
    print(f"Error querying Neo4j: {e}")
    exit(1)

# -----------------------------------------------------------
# 3) Create interactive PyVis network
# -----------------------------------------------------------
net = Network(height="900px", width="100%", directed=True)
net.force_atlas_2based()

# -----------------------------------------------------------
# Helper functions
# -----------------------------------------------------------
def node_display_name(node):
    """Extract display name from node properties"""
    if "name" in node:
        return node["name"]
    if "ns1__storedInDatabaseColumn" in node:
        return node["ns1__storedInDatabaseColumn"]
    if "uri" in node:
        return node["uri"]
    return str(node.identity)

def pick_color(labels):
    """Assign color based on namespace prefix"""
    for label in labels:
        if label.startswith("ns3__"):
            return "#4FC3F7"  # Blue
        if label.startswith("ns2__"):
            return "#81C784"  # Green
        if label.startswith("ns1__"):
            return "#FFCC80"  # Orange
        if label.startswith("ns0__"):
            return "#E57373"  # Red
    return "#B0BEC5"  # Gray

# -----------------------------------------------------------
# 4) Add nodes and edges to network
# -----------------------------------------------------------
added_nodes = set()

for record in data:
    n = record["n"]
    m = record["m"]
    r = record["r"]

    n_id = n.identity
    m_id = m.identity

    # Add source node
    if n_id not in added_nodes:
        n_label = node_display_name(n)
        net.add_node(n_id, label=n_label, title=", ".join(list(n.labels)), color=pick_color(n.labels))
        added_nodes.add(n_id)

    # Add target node
    if m_id not in added_nodes:
        m_label = node_display_name(m)
        net.add_node(m_id, label=m_label, title=", ".join(list(m.labels)), color=pick_color(m.labels))
        added_nodes.add(m_id)

    # Add relationship
    rel_type = type(r).__name__
    net.add_edge(n_id, m_id, title=rel_type, label=rel_type)

print(f"Added {len(added_nodes)} nodes and {len(data)} edges")

# -----------------------------------------------------------
# 5) Export to HTML
# -----------------------------------------------------------
output_file = "owl_visualization.html"
net.write_html(output_file, notebook=False)
print(f"Generated: {output_file}")
