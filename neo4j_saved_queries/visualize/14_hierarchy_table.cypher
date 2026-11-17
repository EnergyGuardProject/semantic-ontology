// 14 · The hierarchy as a table: pilot -> dataset -> what its variables measure -> sensor groups
// View: table.
MATCH (p:Pilot)-[:mp__hasDataset]->(d:Dataset)
OPTIONAL MATCH (d)-[:eg__hasVariable]->(v)
OPTIONAL MATCH (v)-[:INSTANCE_OF]->(c:OntologyClass)
OPTIONAL MATCH (v)<-[:eg__hasMeasurement]-(g:MeasurementGroup)
WITH p, d, count(DISTINCT v) AS variables,
     [k IN collect(DISTINCT replace(c.localName, 'Measurement', '')) WHERE k IS NOT NULL] AS kinds,
     [x IN collect(DISTINCT g.displayName) WHERE x IS NOT NULL] AS groups
RETURN p.displayName AS pilot, d.displayName AS dataset, variables,
       kinds AS kinds_of_measurement, size(groups) AS sensor_groups, groups[0..5] AS example_groups
ORDER BY pilot, dataset;
