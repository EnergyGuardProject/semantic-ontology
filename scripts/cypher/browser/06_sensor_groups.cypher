// 06 · Sensor groups of a pilot (how the original pilot ontology bundled its sensors)
// Edit the pilot: BER, CEA, CARTIF or CIEMAT have groups. View: graph.
WITH 'BER' AS pilot
MATCH path = (g:MeasurementGroup)-[:HAS_MEASUREMENT]->(m:Measurement)
WHERE g.uri CONTAINS '/ontology/' + toLower(pilot) + '#'
RETURN path
LIMIT 300;
