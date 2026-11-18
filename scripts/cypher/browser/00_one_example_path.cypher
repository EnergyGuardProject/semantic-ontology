// 00 · Start here: one sensor and everything it is connected to
// pilot -> dataset -> variable -> its measurement class (-> eg:Measurement), its unit and its sensor group.
// Edit the sensor name on the first line (e.g. TT-D101 for BER, PT305 for CEA, BATA_SOC for CARTIF).
// View: graph.
WITH 'TT-D101' AS sensor
MATCH path = (:Pilot)-[:mp__hasDataset]->(:Dataset)-[:eg__hasVariable]->(v:Measurement {displayName: sensor})
OPTIONAL MATCH cls = (v)-[:INSTANCE_OF]->(:OntologyClass)-[:rdfs__subClassOf]->(:OntologyClass)
OPTIONAL MATCH unit = (v)-[:eg__hasUnit]->()
OPTIONAL MATCH grp = (v)<-[:eg__hasMeasurement]-(:MeasurementGroup)
RETURN path, cls, unit, grp;
