// Name: Semantic second-pass mapping for all_pilots ontology
// Purpose: Improve mapping quality using rdf:type semantics and derived canonical links.
// Run after:
// 1) 01_import_all_pilots_with_n10s.cypher OR 03_import_split_files_safer_for_large_owl.cypher
// 2) 02_map_all_pilots_core_entities.cypher

// 1) Keep constraints/indexes aligned with mapped model
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

CREATE INDEX resource_local_name_idx IF NOT EXISTS
FOR (r:Resource)
ON (r.localName);

CREATE INDEX measurement_table_idx IF NOT EXISTS
FOR (m:Measurement)
ON (m.dbTable);

// 2) Add helper fields for all resources
MATCH (n:Resource)
SET n.localName = coalesce(
      n.localName,
      split(replace(n.uri, '#', '/'), '/')[-1]
    ),
    n.namespace = coalesce(
      n.namespace,
      substring(n.uri, 0, size(n.uri) - size(split(replace(n.uri, '#', '/'), '/')[-1]))
    );

// 3) Label ontology artifacts explicitly (kept separate from domain instances)
MATCH (c:Resource)-[:rdf__type]->(k:Resource)
WHERE k.uri = 'http://www.w3.org/2002/07/owl#Class'
SET c:OntologyClass;

MATCH (p:Resource)-[:rdf__type]->(k:Resource)
WHERE k.uri = 'http://www.w3.org/2002/07/owl#ObjectProperty'
SET p:OntologyObjectProperty;

MATCH (p:Resource)-[:rdf__type]->(k:Resource)
WHERE k.uri = 'http://www.w3.org/2002/07/owl#DatatypeProperty'
SET p:OntologyDatatypeProperty;

// 4) Semantic labeling from rdf:type targets (more precise than URI-only)
MATCH (i:Resource)-[:rdf__type]->(class:Resource)
WHERE class.uri ENDS WITH '#Dataset'
   OR class.uri ENDS WITH '/Dataset'
SET i:Dataset;

MATCH (i:Resource)-[:rdf__type]->(class:Resource)
WHERE class.uri ENDS WITH '#MeasurementGroup'
   OR class.uri ENDS WITH '/MeasurementGroup'
SET i:MeasurementGroup;

MATCH (i:Resource)-[:rdf__type]->(class:Resource)
WHERE class.uri CONTAINS 'Measurement'
SET i:Measurement,
    i.measurementType = coalesce(i.measurementType, class.localName);

// 5) Fallback labels for resources not captured by rdf:type
MATCH (n:Resource)
WHERE n.uri CONTAINS 'Dataset'
SET n:Dataset;

MATCH (n:Resource)
WHERE n.uri ENDS WITH 'MeasurementGroup'
   OR n.uri CONTAINS '#MeasurementGroup'
SET n:MeasurementGroup;

MATCH (n:Resource)
WHERE n.eg__storedInDatabaseColumn IS NOT NULL
   OR n.eg__storedInDatabaseTable IS NOT NULL
SET n:Measurement;

// 6) Unit mapping (QUDT + unit namespace)
MATCH (u:Resource)
WHERE u.uri STARTS WITH 'http://qudt.org/vocab/unit/'
   OR u.uri CONTAINS 'unit:'
SET u:Unit;

// 7) Normalize key properties for easier querying
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

// 8) Pilot tagging based on namespaces (multi-pilot ontology)
MATCH (n:Resource)
WHERE n.uri CONTAINS '/pilot1/'
SET n:Pilot1;

MATCH (n:Resource)
WHERE n.uri CONTAINS '/pilot2#'
SET n:Pilot2;

MATCH (n:Resource)
WHERE n.uri CONTAINS '/pilot3/'
SET n:Pilot3;

MATCH (n:Resource)
WHERE n.uri CONTAINS '/pilot4/'
SET n:Pilot4;

MATCH (n:Resource)
WHERE n.uri CONTAINS '/pilot5/'
SET n:Pilot5;

// 9) Canonical relationship projection for app queries
// Keep original RDF relationships untouched.
MATCH (d:Dataset)-[:eg__hasGroup]->(g:MeasurementGroup)
MERGE (d)-[:HAS_GROUP]->(g);

MATCH (g:MeasurementGroup)-[:eg__hasMeasurement]->(m:Measurement)
MERGE (g)-[:HAS_MEASUREMENT]->(m);

MATCH (m:Measurement)-[:eg__hasUnit]->(u:Unit)
MERGE (m)-[:HAS_UNIT]->(u);

MATCH (m:Measurement)-[:dcterms__isPartOf]->(d:Dataset)
MERGE (m)-[:BELONGS_TO_DATASET]->(d);

// Derived link: group to dataset when a group contains measurements of that dataset
MATCH (g:MeasurementGroup)-[:HAS_MEASUREMENT]->(m:Measurement)-[:BELONGS_TO_DATASET]->(d:Dataset)
MERGE (g)-[:BELONGS_TO_DATASET]->(d);

// 10) Post-mapping quality snapshot
MATCH (d:Dataset)
WITH count(d) AS datasets
MATCH (g:MeasurementGroup)
WITH datasets, count(g) AS groups
MATCH (m:Measurement)
WITH datasets, groups, count(m) AS measurements
MATCH (m2:Measurement)
WHERE m2.hasDbMetadata = false OR m2.hasDbMetadata IS NULL
RETURN datasets, groups, measurements, count(m2) AS measurements_missing_db_metadata;
