// 05 · One pilot: pilot -> datasets -> variables
// Edit the pilot on the first line: RDN, CIEMAT, BER, CEA, CARTIF, REA, ENGREEN
// View: graph. (REA has 536 variables: the LIMIT keeps the Browser responsive.)
WITH 'CEA' AS pilot
MATCH path = (p:Pilot {displayName: pilot})-[:HAS_DATASET]->(:Dataset)
OPTIONAL MATCH vars = (p)-[:HAS_DATASET]->(:Dataset)-[:HAS_VARIABLE]->(:Variable)
RETURN path, vars
LIMIT 300;
