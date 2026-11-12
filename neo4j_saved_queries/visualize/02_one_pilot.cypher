// 02 · One pilot: pilot -> datasets -> variables
// Edit the pilot on the first line: RDN, CIEMAT, BER, CEA, CARTIF, REA, ENGREEN
// View: graph. (REA has 536 variables: the LIMIT keeps the Browser responsive.)
WITH 'CEA' AS pilot
MATCH path = (p:Pilot)-[:mp__hasDataset]->(:Dataset)-[:eg__hasVariable]->(:Measurement)
WHERE p.displayName STARTS WITH pilot
RETURN path
LIMIT 300;
