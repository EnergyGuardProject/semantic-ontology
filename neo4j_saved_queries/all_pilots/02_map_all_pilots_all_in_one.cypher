// Name: All-in-one mapping for all_pilots ontology
// Purpose: Full mapping pipeline in a single script.
// Run after ontology import with n10s.

// -----------------------------------------------------------------------------
// A) Constraints and indexes
// -----------------------------------------------------------------------------
CREATE CONSTRAINT dataset_uri IF NOT EXISTS
FOR (d:Dataset)
REQUIRE d.uri IS UNIQUE;

CREATE CONSTRAINT measurement_group_uri IF NOT EXISTS
FOR (g:MeasurementGroup)
REQUIRE g.uri IS UNIQUE;

CREATE CONSTRAINT measurement_uri IF NOT EXISTS
FOR (m:Measurement)
REQUIRE m.uri IS UNIQUE;

CREATE CONSTRAINT unit_uri IF NOT EXISTS
FOR (u:Unit)
REQUIRE u.uri IS UNIQUE;

CREATE INDEX measurement_code_idx IF NOT EXISTS
FOR (m:Measurement)
ON (m.code);

CREATE INDEX measurement_table_idx IF NOT EXISTS
FOR (m:Measurement)
ON (m.dbTable);

CREATE INDEX resource_local_name_idx IF NOT EXISTS
FOR (r:Resource)
ON (r.localName);

// -----------------------------------------------------------------------------
// B) Helper properties for all resources
// -----------------------------------------------------------------------------
MATCH (n:Resource)
SET n.localName = coalesce(
      n.localName,
      split(replace(n.uri, '#', '/'), '/')[-1]
    ),
    n.namespace = coalesce(
      n.namespace,
      substring(n.uri, 0, size(n.uri) - size(split(replace(n.uri, '#', '/'), '/')[-1]))
    );

// -----------------------------------------------------------------------------
// C) Mark ontology schema artifacts (keep separate from domain instances)
// -----------------------------------------------------------------------------
MATCH (c:Resource)-[:rdf__type]->(k:Resource)
WHERE k.uri = 'http://www.w3.org/2002/07/owl#Class'
SET c:OntologyClass;

MATCH (p:Resource)-[:rdf__type]->(k:Resource)
WHERE k.uri = 'http://www.w3.org/2002/07/owl#ObjectProperty'
SET p:OntologyObjectProperty;

MATCH (p:Resource)-[:rdf__type]->(k:Resource)
WHERE k.uri = 'http://www.w3.org/2002/07/owl#DatatypeProperty'
SET p:OntologyDatatypeProperty;

// -----------------------------------------------------------------------------
// D) Semantic labels from rdf:type targets (preferred)
// -----------------------------------------------------------------------------
MATCH (i:Resource)-[:rdf__type]->(class:Resource)
WITH i, coalesce(class.localName, split(replace(class.uri, '#', '/'), '/')[-1]) AS className
WHERE className IN ['Dataset', 'DataSet']
SET i:Dataset;

MATCH (i:Resource)-[:rdf__type]->(class:Resource)
WITH i, coalesce(class.localName, split(replace(class.uri, '#', '/'), '/')[-1]) AS className
WHERE className = 'MeasurementGroup'
SET i:MeasurementGroup;

MATCH (i:Resource)-[:rdf__type]->(class:Resource)
WITH i, coalesce(class.localName, split(replace(class.uri, '#', '/'), '/')[-1]) AS className
WHERE className CONTAINS 'Measurement'
SET i:Measurement,
    i.measurementType = coalesce(i.measurementType, className);

// -----------------------------------------------------------------------------
// E) Fallback labels (for sparse rdf:type usage)
// -----------------------------------------------------------------------------
MATCH (n:Resource)
WHERE n.uri CONTAINS 'Dataset'
SET n:Dataset;

MATCH (n:Resource)
WHERE n.uri ENDS WITH 'MeasurementGroup'
   OR n.uri CONTAINS '#MeasurementGroup'
SET n:MeasurementGroup;

MATCH (n:Resource)
WHERE n.uri CONTAINS 'Measurement'
   OR n.eg__storedInDatabaseColumn IS NOT NULL
   OR n.eg__storedInDatabaseTable IS NOT NULL
SET n:Measurement;

MATCH (u:Resource)
WHERE u.uri STARTS WITH 'http://qudt.org/vocab/unit/'
   OR u.uri CONTAINS 'unit:'
SET u:Unit;

// -----------------------------------------------------------------------------
// F) Pilot namespace labels
// -----------------------------------------------------------------------------
MATCH (n:Resource)
WHERE n.uri CONTAINS '/pilot1/'
SET n:Pilot1;

MATCH (n:Resource)
WHERE n.uri CONTAINS '/pilot2#'
SET n:Pilot2;


MATCH (n:Resource)
WHERE n.uri CONTAINS '/pilot3/'
SET n:Pilot3;

// --- Specific Pilot3 subdomain labels ---
MATCH (n:Resource)
WHERE n.uri CONTAINS '/pilot3/cea#'
SET n:Pilot3CEA;

MATCH (n:Resource)
WHERE n.uri CONTAINS '/pilot3/cartif#'
SET n:Pilot3CARTIF;

MATCH (n:Resource)
WHERE n.uri CONTAINS '/pilot3/ber#'
SET n:Pilot3BER;

MATCH (n:Resource)
WHERE n.uri CONTAINS '/pilot4/'
SET n:Pilot4;

MATCH (n:Resource)
WHERE n.uri CONTAINS '/pilot5/'
SET n:Pilot5;

// -----------------------------------------------------------------------------
// G) Property normalization
// -----------------------------------------------------------------------------
MATCH (m:Measurement)
SET m.code = coalesce(m.code, trim(m.eg__storedInDatabaseColumn)),
    m.dbTable = coalesce(m.dbTable, trim(m.eg__storedInDatabaseTable)),
    m.displayName = coalesce(m.displayName, m.rdfs__label, m.localName),
    m.hasDbMetadata = (m.eg__storedInDatabaseColumn IS NOT NULL AND m.eg__storedInDatabaseTable IS NOT NULL);

MATCH (d:Dataset)
SET d.displayName = coalesce(d.displayName, d.rdfs__label, d.localName);

MATCH (g:MeasurementGroup)
SET g.displayName = coalesce(g.displayName, g.rdfs__label, g.localName);

MATCH (u:Unit)
SET u.displayName = coalesce(u.displayName, u.rdfs__label, u.localName);

// -----------------------------------------------------------------------------
// H) Canonical relationship projection (predicate harmonization)
// Keep original RDF predicates unchanged.
// -----------------------------------------------------------------------------


// HAS_GROUP variants (expanded for actual types)
MATCH (d:Dataset)-[r]->(g:MeasurementGroup)
WHERE type(r) IN ['eg__hasGroup', 'p3cea__hasGroup', 'ns0__hasGroup']
MERGE (d)-[:HAS_GROUP]->(g);


// HAS_MEASUREMENT variants (expanded for actual types)
MATCH (g:MeasurementGroup)-[r]->(m:Measurement)
WHERE type(r) IN [
  'eg__hasMeasurement',
  'p3cea__hasMeasurement',
  'p3ber__hasMeasurement',
  'p3cartif__hasMeasurement',
  'p2__hasMeasurement',
  'p5engreen__hasMeasurement',
  'p5engreen__hasMeasurements',
  'ns0__hasMeasurement',
  'ns9__hasMeasurement',
  'ns9__hasMeasurements'
]
MERGE (g)-[:HAS_MEASUREMENT]->(m);


// HAS_UNIT variants (expanded for actual types)
MATCH (m:Measurement)-[r]->(u:Unit)
WHERE type(r) IN ['eg__hasUnit', 'p3cea__hasUnit', 'p3cartif__hasUnit', 'p2__hasUnit', 'ns0__hasUnit', 'ns16__hasUnit']
MERGE (m)-[:HAS_UNIT]->(u);

// BELONGS_TO_DATASET variants
MATCH (m:Measurement)-[r]->(d:Dataset)
WHERE type(r) IN [
  'dcterms__isPartOf',
  'p2__recordedInDataset',
  'p3cea__recordedInDataset',
  'p3cartif__recordedInDataset',
  'p1ts__partOfDataset'
]
MERGE (m)-[:BELONGS_TO_DATASET]->(d);

// Derived consistency links from canonical chain
MATCH (d:Dataset)-[:HAS_GROUP]->(g:MeasurementGroup)-[:HAS_MEASUREMENT]->(m:Measurement)
MERGE (m)-[:BELONGS_TO_DATASET]->(d);

MATCH (m:Measurement)-[:BELONGS_TO_DATASET]->(d:Dataset)
WITH m, collect(DISTINCT d.uri) AS ds
SET m.datasetCount = size(ds);

// -----------------------------------------------------------------------------
// I) Final quality snapshot
// -----------------------------------------------------------------------------
MATCH (d:Dataset)
WITH count(d) AS datasets
MATCH (g:MeasurementGroup)
WITH datasets, count(g) AS groups
MATCH (m:Measurement)
WITH datasets, groups, count(m) AS measurements
MATCH ()-[r1:HAS_GROUP]->()
WITH datasets, groups, measurements, count(r1) AS hasGroupEdges
MATCH ()-[r2:HAS_MEASUREMENT]->()
WITH datasets, groups, measurements, hasGroupEdges, count(r2) AS hasMeasurementEdges
MATCH ()-[r3:HAS_UNIT]->()
WITH datasets, groups, measurements, hasGroupEdges, hasMeasurementEdges, count(r3) AS hasUnitEdges
MATCH ()-[r4:BELONGS_TO_DATASET]->()
WITH datasets, groups, measurements, hasGroupEdges, hasMeasurementEdges, hasUnitEdges, count(r4) AS belongsToDatasetEdges
MATCH (m2:Measurement)
WHERE m2.hasDbMetadata = false OR m2.hasDbMetadata IS NULL
RETURN datasets,
       groups,
       measurements,
       hasGroupEdges,
       hasMeasurementEdges,
       hasUnitEdges,
       belongsToDatasetEdges,
       count(m2) AS measurements_missing_db_metadata;
