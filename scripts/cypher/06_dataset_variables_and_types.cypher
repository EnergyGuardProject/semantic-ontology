// 06 · One dataset, its variables, what each one measures and its unit
// Edit the dataset (part of its name is enough). View: graph.
WITH toLower('CARTIF') AS q
MATCH (d:Dataset) WHERE toLower(d.displayName) CONTAINS q
MATCH path = (d)-[:HAS_VARIABLE]->(v:Variable)
OPTIONAL MATCH ty = (v)-[:OF_TYPE]->(:MeasurementType)
OPTIONAL MATCH unit = (v)-[:HAS_UNIT]->(:Unit)
RETURN path, ty, unit
LIMIT 300;
