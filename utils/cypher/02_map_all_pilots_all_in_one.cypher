// Name: All-in-one mapping for all_pilots ontology
// Purpose: Full mapping pipeline in a single script (the only mapping script needed).
// Run after 01_import_all_pilots_with_n10s.cypher.

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
// The import uses handleRDFTypes: LABELS, so rdf:type arrives as node labels
// (owl__Class, eg__TemperatureMeasurement, ...), not as rdf__type relationships.
// -----------------------------------------------------------------------------
MATCH (c:owl__Class) SET c:OntologyClass;
MATCH (p:owl__ObjectProperty) SET p:OntologyObjectProperty;
MATCH (p:owl__DatatypeProperty) SET p:OntologyDatatypeProperty;

// -----------------------------------------------------------------------------
// D) Semantic labels
// -----------------------------------------------------------------------------
// Datasets: everything a pilot links with hasDataset (all are dcat:Dataset)
MATCH (p:Resource)-[r]->(d:Resource)
WHERE type(r) ENDS WITH '__hasDataset'
SET d:Dataset;

MATCH (d:dcat__Dataset) SET d:Dataset;

// Groups: whatever bundles sensors with hasMeasurement (some pilots type their groups
// with a measurement class, so the structure is the reliable signal)
MATCH (g:Resource)-[:eg__hasMeasurement]->()
SET g:MeasurementGroup;

MATCH (n:Resource)
WHERE any(l IN labels(n) WHERE l ENDS WITH '__MeasurementGroup')
SET n:MeasurementGroup;

// Measurements: every variable of a dataset, plus individuals typed with a *Measurement class
MATCH (d:Resource)-[r]->(v:Resource)
WHERE type(r) ENDS WITH '__hasVariable'
SET v:Measurement;

MATCH (i:Resource)
WHERE NOT i:OntologyClass AND NOT i:MeasurementGroup
  AND any(l IN labels(i) WHERE l ENDS WITH 'Measurement' AND l CONTAINS '__')
SET i:Measurement;

// measurementType = the most specific measurement class, e.g. 'TemperatureMeasurement'
MATCH (i:Measurement)
WITH i, [l IN labels(i) WHERE l ENDS WITH 'Measurement' AND l CONTAINS '__' | split(l, '__')[1]] AS types
WHERE size(types) > 0
SET i.measurementType = coalesce(i.measurementType, types[0]);

// -----------------------------------------------------------------------------
// E) Fallback labels (sample individuals of pilots without metadata, e.g. RDN)
// -----------------------------------------------------------------------------
MATCH (n:Resource)
WHERE n.eg__storedInDatabaseColumn IS NOT NULL AND NOT n:Dataset
SET n:Measurement;

MATCH (u:Resource)
WHERE u.uri STARTS WITH 'http://qudt.org/vocab/unit/'
SET u:Unit;

// -----------------------------------------------------------------------------
// F) Pilot labels (one per organisation)
// -----------------------------------------------------------------------------
MATCH (n:Resource)
WHERE n.uri CONTAINS '/ontology/rdn'
SET n:RDN;

MATCH (n:Resource)
WHERE n.uri CONTAINS '/ontology/ciemat#'
SET n:CIEMAT;

MATCH (n:Resource)
WHERE n.uri CONTAINS '/ontology/ber#'
SET n:BER;

MATCH (n:Resource)
WHERE n.uri CONTAINS '/ontology/cea#'
SET n:CEA;

MATCH (n:Resource)
WHERE n.uri CONTAINS '/ontology/cartif#'
SET n:CARTIF;

MATCH (n:Resource)
WHERE n.uri CONTAINS '/ontology/rea#'
SET n:REA;

MATCH (n:Resource)
WHERE n.uri CONTAINS '/ontology/engreen#'
SET n:ENGREEN;

// Pilot nodes: label them and give them a readable name (they are classes of the pilot tree)
MATCH (:Resource {uri: 'https://www.energyguard.eu/ontology/merged-pilots#Pilots'})-[:mp__hasPilot]->(p)
SET p:Pilot, p.displayName = coalesce(p.rdfs__label[0], p.localName);

MATCH (:Pilot)-[:mp__hasSubPilot]->(s)
SET s:SubPilot, s.displayName = coalesce(s.rdfs__label[0], s.localName);

MATCH (c:OntologyClass) WHERE c.displayName IS NULL
SET c.displayName = coalesce(c.rdfs__label[0], c.localName);

// -----------------------------------------------------------------------------
// G) Property normalization
// n10s stores values as lists (handleMultival: 'ARRAY'); take the first element.
// Where the data lives (see docs/ontology-guide.md):
//   dataset  -> eg:storedInDatabase (TEF<n>_<pilot>), eg:storedInDatabaseTable, eg:tableLayout
//   variable -> eg:dataLakeSensorId | eg:dataLakeSensorPattern (long layout, public.f_tsdata)
//               eg:storedInDatabaseColumn (wide tables, or d_calendar.datetime for timestamps)
// -----------------------------------------------------------------------------
MATCH (m:Measurement)
WITH m,
     CASE WHEN m.rdfs__label IS :: LIST<ANY> THEN m.rdfs__label[0] ELSE m.rdfs__label END AS label,
     CASE WHEN m.eg__dataLakeSensorId IS :: LIST<ANY> THEN m.eg__dataLakeSensorId[0] ELSE m.eg__dataLakeSensorId END AS sid,
     CASE WHEN m.eg__dataLakeSensorPattern IS :: LIST<ANY> THEN m.eg__dataLakeSensorPattern[0] ELSE m.eg__dataLakeSensorPattern END AS pattern,
     CASE WHEN m.eg__storedInDatabaseColumn IS :: LIST<ANY> THEN m.eg__storedInDatabaseColumn[0] ELSE m.eg__storedInDatabaseColumn END AS col,
     CASE WHEN m.eg__dataLakeMatch IS :: LIST<ANY> THEN m.eg__dataLakeMatch[0] ELSE m.eg__dataLakeMatch END AS how
SET m.displayName = coalesce(m.displayName, label, m.localName),
    m.lakeSensorId = sid,
    m.lakeSensorPattern = pattern,
    m.lakeColumn = col,
    m.lakeMatch = coalesce(how, 'none'),
    m.code = coalesce(sid, pattern, col);

MATCH (d:Dataset)-[r]->(m:Measurement)
WHERE type(r) ENDS WITH '__hasVariable'
WITH m, d,
     CASE WHEN d.eg__storedInDatabase IS :: LIST<ANY> THEN d.eg__storedInDatabase[0] ELSE d.eg__storedInDatabase END AS db,
     CASE WHEN d.eg__storedInDatabaseTable IS :: LIST<ANY> THEN d.eg__storedInDatabaseTable ELSE [d.eg__storedInDatabaseTable] END AS tables,
     CASE WHEN d.eg__tableLayout IS :: LIST<ANY> THEN d.eg__tableLayout[0] ELSE d.eg__tableLayout END AS layout
WHERE db IS NOT NULL
UNWIND tables AS tbl
WITH m, collect(DISTINCT db) AS dbs, collect(DISTINCT layout) AS layouts, collect(DISTINCT tbl) AS tbls
SET m.database = dbs[0], m.databases = dbs, m.dbTable = tbls[0], m.dbTables = tbls, m.tableLayout = layouts[0];

// pilots without metadata (RDN samples) still carry table/column on the measurement itself
MATCH (m:Measurement)
WHERE m.dbTable IS NULL AND m.eg__storedInDatabaseTable IS NOT NULL
SET m.dbTable = CASE WHEN m.eg__storedInDatabaseTable IS :: LIST<ANY> THEN m.eg__storedInDatabaseTable[0]
                     ELSE m.eg__storedInDatabaseTable END;

MATCH (m:Measurement)
SET m.hasDbMetadata = (m.dbTable IS NOT NULL AND m.code IS NOT NULL);

MATCH (n:Resource)
WHERE (n:Dataset OR n:MeasurementGroup OR n:Unit) AND n.displayName IS NULL
SET n.displayName = coalesce(
      CASE WHEN n.rdfs__label IS :: LIST<ANY> THEN n.rdfs__label[0] ELSE n.rdfs__label END,
      n.localName);

// -----------------------------------------------------------------------------
// H) Canonical relationships (the original RDF relationships are kept)
// After the ontology clean-up every pilot uses the shared eg: predicates.
// -----------------------------------------------------------------------------
MATCH (d:Dataset)-[:eg__hasGroup]->(g:MeasurementGroup)
MERGE (d)-[:HAS_GROUP]->(g);

MATCH (g:MeasurementGroup)-[r]->(m:Measurement)
WHERE type(r) IN ['eg__hasMeasurement', 'engreen__hasMeasurements']
MERGE (g)-[:HAS_MEASUREMENT]->(m);

MATCH (m:Measurement)-[:eg__hasUnit]->(u:Unit)
MERGE (m)-[:HAS_UNIT]->(u);

MATCH (d:Dataset)-[:eg__hasVariable]->(m:Measurement)
MERGE (m)-[:BELONGS_TO_DATASET]->(d);

MATCH (m:Measurement)-[:dcterms__isPartOf]->(d:Dataset)
MERGE (m)-[:BELONGS_TO_DATASET]->(d);

// Measurement -> its class node. Types arrive as labels (eg__TemperatureMeasurement); this makes
// them visible as edges, which the visualisation queries use.
MATCH (m:Measurement)
UNWIND [l IN labels(m) WHERE (l ENDS WITH 'Measurement' AND l CONTAINS '__')
                            OR l IN ['eg__TimeColumn', 'eg__IdentifierColumn']] AS lbl
MATCH (c:OntologyClass {uri: n10s.rdf.fullUriFromShortForm(lbl)})
MERGE (m)-[:INSTANCE_OF]->(c);

// Derived: a group belongs to the datasets of its measurements
MATCH (g:MeasurementGroup)-[:HAS_MEASUREMENT]->(m:Measurement)-[:BELONGS_TO_DATASET]->(d:Dataset)
MERGE (g)-[:BELONGS_TO_DATASET]->(d);

MATCH (m:Measurement)-[:BELONGS_TO_DATASET]->(d:Dataset)
WITH m, count(DISTINCT d) AS n
SET m.datasetCount = n;

// -----------------------------------------------------------------------------
// I) Final quality snapshot (each count runs on its own, so an empty one shows 0)
// -----------------------------------------------------------------------------
CALL () { MATCH (d:Dataset) RETURN count(d) AS datasets }
CALL () { MATCH (g:MeasurementGroup) RETURN count(g) AS groups }
CALL () { MATCH (m:Measurement) RETURN count(m) AS measurements }
CALL () { MATCH ()-[r:HAS_GROUP]->() RETURN count(r) AS hasGroupEdges }
CALL () { MATCH ()-[r:HAS_MEASUREMENT]->() RETURN count(r) AS hasMeasurementEdges }
CALL () { MATCH ()-[r:HAS_UNIT]->() RETURN count(r) AS hasUnitEdges }
CALL () { MATCH ()-[r:BELONGS_TO_DATASET]->() RETURN count(r) AS belongsToDatasetEdges }
CALL () { MATCH (m:Measurement) WHERE NOT coalesce(m.hasDbMetadata, false) RETURN count(m) AS measurements_missing_db_metadata }
RETURN datasets, groups, measurements, hasGroupEdges, hasMeasurementEdges, hasUnitEdges,
       belongsToDatasetEdges, measurements_missing_db_metadata;
