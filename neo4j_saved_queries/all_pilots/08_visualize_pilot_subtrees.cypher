// Name: Visualize pilot subtrees
// Purpose: Render the imported graph grouped by pilot labels and their connected subtrees.
// This query is meant for Neo4j Browser graph view.
// Run this in Browser, not cypher-shell, if you want a visual graph.
// It shows relationships touching any node tagged Pilot1..Pilot5.

MATCH (n)-[r]->(m)
WHERE any(lbl IN labels(n) WHERE lbl STARTS WITH 'Pilot')
   OR any(lbl IN labels(m) WHERE lbl STARTS WITH 'Pilot')
RETURN n, r, m
LIMIT 500;
