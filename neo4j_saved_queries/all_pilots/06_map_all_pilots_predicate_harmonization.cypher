// Name: Predicate harmonization for all_pilots ontology
// Purpose: Unify pilot-specific predicate variants into canonical relationships.
// Run after core/semantic mapping scripts.

// Canonical edge set used by application queries:
// - HAS_GROUP
// - HAS_MEASUREMENT
// - HAS_UNIT
// - BELONGS_TO_DATASET

// 1) HAS_GROUP variants
MATCH (d:Dataset)-[:eg__hasGroup]->(g:MeasurementGroup)
MERGE (d)-[:HAS_GROUP]->(g);

MATCH (d:Dataset)-[:p3cea__hasGroup]->(g:MeasurementGroup)
MERGE (d)-[:HAS_GROUP]->(g);

MATCH (d:Dataset)-[:p5engreen__hasDataset]->(g:MeasurementGroup)
MERGE (d)-[:HAS_GROUP]->(g);

// 2) HAS_MEASUREMENT variants
MATCH (g:MeasurementGroup)-[:eg__hasMeasurement]->(m:Measurement)
MERGE (g)-[:HAS_MEASUREMENT]->(m);

MATCH (g:MeasurementGroup)-[:p3cea__hasMeasurement]->(m:Measurement)
MERGE (g)-[:HAS_MEASUREMENT]->(m);

MATCH (g:MeasurementGroup)-[:p3ber__hasMeasurement]->(m:Measurement)
MERGE (g)-[:HAS_MEASUREMENT]->(m);

MATCH (g:MeasurementGroup)-[:p3cartif__hasMeasurement]->(m:Measurement)
MERGE (g)-[:HAS_MEASUREMENT]->(m);

MATCH (g:MeasurementGroup)-[:p2__hasMeasurement]->(m:Measurement)
MERGE (g)-[:HAS_MEASUREMENT]->(m);

MATCH (g:MeasurementGroup)-[:p5engreen__hasMeasurement]->(m:Measurement)
MERGE (g)-[:HAS_MEASUREMENT]->(m);

MATCH (g:MeasurementGroup)-[:p5engreen__hasMeasurements]->(m:Measurement)
MERGE (g)-[:HAS_MEASUREMENT]->(m);

// 3) HAS_UNIT variants
MATCH (m:Measurement)-[:eg__hasUnit]->(u)
MERGE (m)-[:HAS_UNIT]->(u);

MATCH (m:Measurement)-[:p3cea__hasUnit]->(u)
MERGE (m)-[:HAS_UNIT]->(u);

MATCH (m:Measurement)-[:p3cartif__hasUnit]->(u)
MERGE (m)-[:HAS_UNIT]->(u);

MATCH (m:Measurement)-[:p2__hasUnit]->(u)
MERGE (m)-[:HAS_UNIT]->(u);

// 4) BELONGS_TO_DATASET variants
MATCH (m:Measurement)-[:dcterms__isPartOf]->(d:Dataset)
MERGE (m)-[:BELONGS_TO_DATASET]->(d);

MATCH (m:Measurement)-[:p2__recordedInDataset]->(d:Dataset)
MERGE (m)-[:BELONGS_TO_DATASET]->(d);

MATCH (m:Measurement)-[:p3cea__recordedInDataset]->(d:Dataset)
MERGE (m)-[:BELONGS_TO_DATASET]->(d);

MATCH (m:Measurement)-[:p3cartif__recordedInDataset]->(d:Dataset)
MERGE (m)-[:BELONGS_TO_DATASET]->(d);

MATCH (m:Measurement)-[:p1ts__partOfDataset]->(d:Dataset)
MERGE (m)-[:BELONGS_TO_DATASET]->(d);

// 5) Derived consistency links
MATCH (d:Dataset)-[:HAS_GROUP]->(g:MeasurementGroup)-[:HAS_MEASUREMENT]->(m:Measurement)
MERGE (m)-[:BELONGS_TO_DATASET]->(d);

MATCH (m:Measurement)-[:BELONGS_TO_DATASET]->(d:Dataset)
WITH m, collect(DISTINCT d.uri) AS ds
SET m.datasetCount = size(ds);

// 6) Quality snapshot
MATCH (d:Dataset)
WITH count(d) AS datasets
MATCH (g:MeasurementGroup)
WITH datasets, count(g) AS groups
MATCH (m:Measurement)
WITH datasets, groups, count(m) AS measurements
MATCH ()-[r:HAS_MEASUREMENT]->()
WITH datasets, groups, measurements, count(r) AS hasMeasurementEdges
MATCH ()-[u:HAS_UNIT]->()
WITH datasets, groups, measurements, hasMeasurementEdges, count(u) AS hasUnitEdges
MATCH ()-[b:BELONGS_TO_DATASET]->()
RETURN datasets, groups, measurements, hasMeasurementEdges, hasUnitEdges, count(b) AS belongsToDatasetEdges;
