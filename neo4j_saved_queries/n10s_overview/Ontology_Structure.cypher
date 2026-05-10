// Name: Ontology Structure (duplicate entry / n10s overview)
MATCH (c1:Resource)-[r]->(c2:Resource)
RETURN DISTINCT labels(c1) AS FromLabels, type(r) AS Relation, labels(c2) AS ToLabels
ORDER BY FromLabels, Relation;
