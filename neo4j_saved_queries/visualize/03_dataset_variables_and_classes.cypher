// 03 · One dataset, its variables and what kind of measurement each one is
// Edit the dataset (part of its name is enough). View: graph.
WITH 'CARTIF' AS dataset
MATCH (d:Dataset) WHERE d.displayName CONTAINS dataset
MATCH path = (d)-[:eg__hasVariable]->(v:Measurement)
OPTIONAL MATCH cls = (v)-[:INSTANCE_OF]->(:OntologyClass)
RETURN path, cls
LIMIT 400;
