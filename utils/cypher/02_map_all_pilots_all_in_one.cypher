// Name: Convenience layer for the all_pilots ontology
// Purpose: after the import, add short labels, shortcut properties and canonical relationships on top of the
//          standard terms, so the saved queries stay short. Nothing here changes the imported RDF.
// Run after 01_import_all_pilots_with_n10s.cypher.
//
//   Labels         Pilot (foaf:Organization that publishes datasets), Dataset (dcat:Dataset), Variable (eg:Variable),
//                  MeasurementType (sosa:ObservableProperty), Platform (sosa:Platform), Unit (QUDT unit)
//   Relationships  (Pilot)-[:HAS_DATASET]->(Dataset)        (Dataset)-[:HAS_VARIABLE]->(Variable)
//                  (Variable)-[:OF_TYPE]->(MeasurementType) (Variable)-[:HOSTED_BY]->(Platform)
//                  (Variable)-[:HAS_UNIT]->(Unit)
//   Shortcuts      displayName; on variables lakeSensorId, lakeSensorPattern, lakeColumn, lakeMatch, measurementType;
//                  on datasets database, dbTable, dbTables, tableLayout

// A) Constraints and indexes
CREATE CONSTRAINT dataset_uri IF NOT EXISTS FOR (d:Dataset) REQUIRE d.uri IS UNIQUE;
CREATE CONSTRAINT variable_uri IF NOT EXISTS FOR (v:Variable) REQUIRE v.uri IS UNIQUE;
CREATE CONSTRAINT unit_uri IF NOT EXISTS FOR (u:Unit) REQUIRE u.uri IS UNIQUE;
CREATE INDEX resource_local_name_idx IF NOT EXISTS FOR (r:Resource) ON (r.localName);

// B) Short name of every resource
MATCH (n:Resource) SET n.localName = coalesce(n.localName, split(replace(n.uri, '#', '/'), '/')[-1]);

// C) Short labels (types arrive as labels like dcat__Dataset because the import uses handleRDFTypes: LABELS)
MATCH (d:dcat__Dataset) SET d:Dataset;
MATCH (:dcat__Dataset)-[:dcterms__publisher]->(p:Resource) SET p:Pilot;
MATCH (v:eg__Variable) SET v:Variable;
MATCH (t:sosa__ObservableProperty) SET t:MeasurementType;
MATCH (p:sosa__Platform) SET p:Platform;
MATCH (u:Resource) WHERE u.uri STARTS WITH 'http://qudt.org/vocab/unit/' SET u:Unit;

// Pilot nodes carry the pilot's name as a label too (BER, CEA, ...)
MATCH (n:Resource) WHERE n.uri CONTAINS '/ontology/rdn' SET n:RDN;
MATCH (n:Resource) WHERE n.uri CONTAINS '/ontology/ciemat#' SET n:CIEMAT;
MATCH (n:Resource) WHERE n.uri CONTAINS '/ontology/ber#' SET n:BER;
MATCH (n:Resource) WHERE n.uri CONTAINS '/ontology/cea#' SET n:CEA;
MATCH (n:Resource) WHERE n.uri CONTAINS '/ontology/cartif#' SET n:CARTIF;
MATCH (n:Resource) WHERE n.uri CONTAINS '/ontology/rea#' SET n:REA;
MATCH (n:Resource) WHERE n.uri CONTAINS '/ontology/engreen#' SET n:ENGREEN;

// D) A readable name for everything that has one (n10s stores values as lists: take the first)
MATCH (n:Resource)
WITH n, head([x IN [n.rdfs__label, n.skos__prefLabel, n.dcterms__title, n.qudt__symbol] WHERE x IS NOT NULL]) AS first
SET n.displayName = coalesce(CASE WHEN first IS :: LIST<ANY> THEN first[0] ELSE first END, n.localName);

// E) Canonical relationships (the RDF relationships stay too)
MATCH (d:Dataset)-[:dcterms__publisher]->(p:Pilot) MERGE (p)-[:HAS_DATASET]->(d);
MATCH (d:Dataset)-[:sch__variableMeasured]->(v:Variable) MERGE (d)-[:HAS_VARIABLE]->(v);
MATCH (v:Variable)-[:qudt__hasUnit]->(u:Unit) MERGE (v)-[:HAS_UNIT]->(u);
MATCH (v:Variable)-[r]->(t:MeasurementType) WHERE type(r) IN ['sosa__observes', 'eg__relatesToProperty'] MERGE (v)-[:OF_TYPE]->(t);
MATCH (v:Variable)-[:sosa__isHostedBy]->(p:Platform) MERGE (v)-[:HOSTED_BY]->(p);

// F) Where the data lives: the lake table is on the dataset's distribution
MATCH (d:Dataset)-[:dcat__distribution]->(x)
WITH d, x,
     CASE WHEN x.eg__storedInDatabase IS :: LIST<ANY> THEN x.eg__storedInDatabase[0] ELSE x.eg__storedInDatabase END AS db,
     CASE WHEN x.eg__storedInDatabaseTable IS :: LIST<ANY> THEN x.eg__storedInDatabaseTable ELSE [x.eg__storedInDatabaseTable] END AS tables,
     CASE WHEN x.eg__tableLayout IS :: LIST<ANY> THEN x.eg__tableLayout[0] ELSE x.eg__tableLayout END AS layout
WHERE db IS NOT NULL
SET d.database = db, d.dbTable = tables[0], d.dbTables = tables, d.tableLayout = layout;

// G) Shortcut properties on variables
MATCH (v:Variable)
WITH v,
     CASE WHEN v.eg__dataLakeSensorId IS :: LIST<ANY> THEN v.eg__dataLakeSensorId[0] ELSE v.eg__dataLakeSensorId END AS sid,
     CASE WHEN v.eg__dataLakeSensorPattern IS :: LIST<ANY> THEN v.eg__dataLakeSensorPattern[0] ELSE v.eg__dataLakeSensorPattern END AS pattern,
     CASE WHEN v.eg__storedInDatabaseColumn IS :: LIST<ANY> THEN v.eg__storedInDatabaseColumn[0] ELSE v.eg__storedInDatabaseColumn END AS col,
     CASE WHEN v.eg__dataLakeMatch IS :: LIST<ANY> THEN v.eg__dataLakeMatch[0] ELSE v.eg__dataLakeMatch END AS how
SET v.lakeSensorId = sid, v.lakeSensorPattern = pattern, v.lakeColumn = col,
    v.lakeMatch = coalesce(how, 'none');     // no match recorded means the variable is not in the lake

MATCH (v:Variable)-[:OF_TYPE]->(t:MeasurementType) SET v.measurementType = t.displayName;

// H) Final quality snapshot (each count runs on its own, so an empty one shows 0)
CALL () { MATCH (p:Pilot) RETURN count(p) AS pilots }
CALL () { MATCH (d:Dataset) RETURN count(d) AS datasets }
CALL () { MATCH (v:Variable) RETURN count(v) AS variables }
CALL () { MATCH ()-[r:HAS_DATASET]->() RETURN count(r) AS hasDatasetEdges }
CALL () { MATCH ()-[r:OF_TYPE]->() RETURN count(r) AS ofTypeEdges }
CALL () { MATCH ()-[r:HOSTED_BY]->() RETURN count(r) AS hostedByEdges }
CALL () { MATCH ()-[r:HAS_UNIT]->() RETURN count(r) AS hasUnitEdges }
RETURN pilots, datasets, variables, hasDatasetEdges, ofTypeEdges, hostedByEdges, hasUnitEdges;
