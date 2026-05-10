// Name: Explore all triples (subject-predicate-object)
MATCH (s:Resource)-[p]->(o)
RETURN s.iri AS Subject, type(p) AS Predicate, 
       CASE WHEN o:Resource THEN o.iri ELSE o END AS Object
LIMIT 100;
