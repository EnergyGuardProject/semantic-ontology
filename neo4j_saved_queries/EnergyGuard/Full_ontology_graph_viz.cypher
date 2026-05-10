// Name: Full ontology graph viz
MATCH (n)-[r]->(m)
WHERE any(l IN labels(n) WHERE l STARTS WITH "ns") 
   OR any(l IN labels(m) WHERE l STARTS WITH "ns")
RETURN n, r, m
LIMIT 300;
