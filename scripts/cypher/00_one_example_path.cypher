// 00 · Start here: one sensor and everything it is connected to
// pilot -> dataset -> variable -> what it measures (measurement type), its unit and the equipment that hosts it.
// Edit the sensor name on the first line (e.g. TT-D101 for BER, PT305 for CEA, BATA_SOC for CARTIF).
// View: graph.
WITH 'TT-D101' AS sensor
MATCH path = (:Pilot)-[:HAS_DATASET]->(:Dataset)-[:HAS_VARIABLE]->(v:Variable {displayName: sensor})
OPTIONAL MATCH ty = (v)-[:OF_TYPE]->(:MeasurementType)
OPTIONAL MATCH unit = (v)-[:HAS_UNIT]->()
OPTIONAL MATCH eq = (v)-[:HOSTED_BY]->(:Platform)
RETURN path, ty, unit, eq;
