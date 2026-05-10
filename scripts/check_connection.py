from neo4j import GraphDatabase

# Connection details
uri = "neo4j://127.0.0.1:7687"
user = "neo4j"
password = "neo4j@energyguard"
database = "pilot2"

# Create driver instance
driver = GraphDatabase.driver(uri, auth=(user, password))

# Test connectivity
with driver.session(database=database) as session:
    result = session.run("RETURN 1 AS test")
    for record in result:
        print(record["test"])

driver.close()
