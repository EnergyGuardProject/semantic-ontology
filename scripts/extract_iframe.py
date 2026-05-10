from py2neo import Graph
from pyvis.network import Network  # ← FIXED

# -----------------------------------------------------------
# 1) Connect to Neo4j
# -----------------------------------------------------------
graph = Graph(
    "bolt://127.0.0.1:7687",
    auth=("neo4j", "neo4j@energyguard"),
    name="pilot2"
)

# -----------------------------------------------------------
# 2) Run YOUR query
# -----------------------------------------------------------
query = """
MATCH (n)-[r]->(m)
WHERE any(label IN labels(n) WHERE label STARTS WITH 'ns') 
   OR any(label IN labels(m) WHERE label STARTS WITH 'ns')
RETURN n, r, m
LIMIT 300
"""

data = graph.run(query).data()

# -----------------------------------------------------------
# 3) Create interactive PyVis network
# -----------------------------------------------------------
net = Network(height="900px", width="100%", directed=True)  # ← FIXED
net.force_atlas_2based()

# -----------------------------------------------------------
# Helper
# -----------------------------------------------------------
def node_display_name(node):
    if "name" in node:
        return node["name"]
    if "ns1__storedInDatabaseColumn" in node:
        return node["ns1__storedInDatabaseColumn"]
    if "uri" in node:
        return node["uri"]
    return str(node.identity)

# -----------------------------------------------------------
# 4) Add nodes + edges
# -----------------------------------------------------------
for record in data:
    n = record["n"]
    m = record["m"]
    r = record["r"]

    n_id = n.identity
    m_id = m.identity

    n_label = node_display_name(n)
    m_label = node_display_name(m)

    def pick_color(labels):
        for l in labels:
            if l.startswith("ns3__"):
                return "#4FC3F7"
            if l.startswith("ns2__"):
                return "#81C784"
            if l.startswith("ns1__"):
                return "#FFCC80"
            if l.startswith("ns0__"):
                return "#E57373"
        return "#B0BEC5"

    net.add_node(n_id, label=n_label, title=", ".join(list(n.labels)), color=pick_color(n.labels))
    net.add_node(m_id, label=m_label, title=", ".join(list(m.labels)), color=pick_color(m.labels))

    rel_type = type(r).__name__
    net.add_edge(n_id, m_id, title=rel_type, label=rel_type)

# -----------------------------------------------------------
# 5) Export
# -----------------------------------------------------------
net.write_html("ontology_graph.html", notebook=False)

print("Generated: ontology_graph.html")
