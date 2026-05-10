// Name: Post-import validation for large OWL loads
// Purpose: Check ontology load completeness and mapping readiness.

// 1) Core graph size
MATCH (n:Resource)
WITH count(n) AS resources
MATCH ()-[r]->()
RETURN resources, count(r) AS relationships;

// 2) Namespace distribution (helps detect missing pilot imports)
MATCH (n:Resource)
WITH n,
CASE
  WHEN n.uri CONTAINS '/pilot1/' THEN 'pilot1'
  WHEN n.uri CONTAINS '/pilot2#' THEN 'pilot2'
  WHEN n.uri CONTAINS '/pilot3/' THEN 'pilot3'
  WHEN n.uri CONTAINS '/pilot4/' THEN 'pilot4'
  WHEN n.uri CONTAINS '/pilot5/' THEN 'pilot5'
  ELSE 'other'
END AS bucket
RETURN bucket, count(*) AS nodes
ORDER BY nodes DESC;

// 3) Top predicates by frequency (spot unexpected ontology patterns)
MATCH ()-[r]->()
RETURN type(r) AS predicate, count(*) AS freq
ORDER BY freq DESC
LIMIT 30;

// 4) Mapping readiness: measurements missing db metadata
MATCH (m:Measurement)
WHERE m.eg__storedInDatabaseColumn IS NULL
   OR m.eg__storedInDatabaseTable IS NULL
RETURN count(m) AS measurements_missing_db_metadata;

// 5) Mapping readiness: datasets without groups
MATCH (d:Dataset)
WHERE NOT (d)-[:HAS_GROUP]->(:MeasurementGroup)
RETURN count(d) AS datasets_without_groups;

// 6) Mapping readiness: groups without measurements
MATCH (g:MeasurementGroup)
WHERE NOT (g)-[:HAS_MEASUREMENT]->(:Measurement)
RETURN count(g) AS groups_without_measurements;
