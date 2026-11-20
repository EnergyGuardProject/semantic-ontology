// 09 · The equipment of a pilot (sosa:Platform) and the variables it hosts
// Edit the pilot: BER, CEA, CARTIF, CIEMAT or ENGREEN have equipment. View: graph.
WITH 'BER' AS pilot
MATCH path = (:Pilot {displayName: pilot})-[:HAS_DATASET]->(:Dataset)-[:HAS_VARIABLE]->(v:Variable)-[:HOSTED_BY]->(:Platform)
RETURN path
LIMIT 300;
