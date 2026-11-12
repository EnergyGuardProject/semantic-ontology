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
  WHEN n.uri CONTAINS '/ontology/rdn' THEN 'RDN'
  WHEN n.uri CONTAINS '/ontology/ciemat#' THEN 'CIEMAT'
  WHEN n.uri CONTAINS '/ontology/ber#' THEN 'BER'
  WHEN n.uri CONTAINS '/ontology/cea#' THEN 'CEA'
  WHEN n.uri CONTAINS '/ontology/cartif#' THEN 'CARTIF'
  WHEN n.uri CONTAINS '/ontology/rea#' THEN 'REA'
  WHEN n.uri CONTAINS '/ontology/engreen#' THEN 'ENGREEN'
  ELSE 'other'
END AS bucket
RETURN bucket, count(*) AS nodes
ORDER BY nodes DESC;

// 3) Top predicates by frequency (spot unexpected ontology patterns)
MATCH ()-[r]->()
RETURN type(r) AS predicate, count(*) AS freq
ORDER BY freq DESC
LIMIT 30;

// 4) Data lake coverage per pilot (run after 02): how variables were located
MATCH (p:Resource)-[:mp__hasDataset]->(d:Dataset)-[:eg__hasVariable]->(m:Measurement)
WITH DISTINCT p, m
RETURN p.rdfs__label[0] AS pilot, m.lakeMatch AS located_by, count(*) AS variables
ORDER BY pilot, located_by;

// 5) Datasets without a data-lake location
MATCH (p:Resource)-[:mp__hasDataset]->(d:Dataset)
WHERE d.eg__storedInDatabase IS NULL
RETURN p.rdfs__label[0] AS pilot, collect(d.displayName) AS datasets_not_in_lake
ORDER BY pilot;

// 6) Groups without measurements
MATCH (g:MeasurementGroup)
WHERE NOT (g)-[:HAS_MEASUREMENT]->(:Measurement)
RETURN count(g) AS groups_without_measurements;
