// 05 · One kind of measurement across all pilots
// Edit the class: TemperatureMeasurement, PressureMeasurement, FlowMeasurement, PowerMeasurement,
// EnergyMeasurement, CurrentMeasurement, VoltageMeasurement, StateMeasurement, ...
// View: graph. Pilots -> datasets -> variables -> the class.
WITH 'PressureMeasurement' AS cls
MATCH path = (:Pilot)-[:mp__hasDataset]->(:Dataset)-[:eg__hasVariable]->(:Measurement)-[:INSTANCE_OF]->(c:OntologyClass)
WHERE c.localName = cls
RETURN path
LIMIT 300;
