from neo4j import GraphDatabase

# === Connection info ===
uri = "bolt://energyguard.epu.ntua.gr:7687"    # Neo4j Bolt protocol
user = "neo4j"
password = "neo4j@energyguard"    # Neo4j password
database = "neo4j"               # Default database (where OWL is imported)

# === Connect to Neo4j ===
driver = GraphDatabase.driver(uri, auth=(user, password))

def evaluate_schema(tx):
    # 1️⃣ Get all labels
    labels_query = "CALL db.labels()"
    labels = [row["label"] for row in tx.run(labels_query)]
    
    # 2️⃣ Get all relationship types
    rels_query = "CALL db.relationshipTypes()"
    relationships = [row["relationshipType"] for row in tx.run(rels_query)]
    
    # 3️⃣ Sample nodes and properties per label
    nodes_props = {}
    for label in labels:
        sample_query = f"""
        MATCH (n:`{label}`)
        RETURN n LIMIT 5
        """
        nodes_props[label] = [dict(record["n"]) for record in tx.run(sample_query)]
    
    return labels, relationships, nodes_props

with driver.session(database=database) as session:
    labels, relationships, nodes_props = session.execute_read(evaluate_schema)

# === Print results ===
print("=== Labels in the ontology ===")
for l in labels:
    print("-", l)

print("\n=== Relationship types ===")
for r in relationships:
    print("-", r)

print("\n=== Sample nodes per label ===")
for label, samples in nodes_props.items():
    print(f"\nLabel: {label}")
    for s in samples:
        print(" ", s)
