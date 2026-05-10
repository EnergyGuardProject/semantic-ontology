// Name: Visualize Pilot3 graph only
// Purpose: Single-statement graph visualization for Neo4j Browser.

MATCH (n)-[r]-(m)
WHERE 'Pilot3' IN labels(n) OR 'Pilot3' IN labels(m)
RETURN n, r, m
LIMIT 300;
