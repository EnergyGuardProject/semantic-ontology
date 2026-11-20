// 08 · One kind of measurement across all pilots
// Edit the type: Temperature, Pressure, Flow, Power, Energy, Current, Voltage, State, Solar Radiation, ... (see 07)
// View: graph. Pilots -> datasets -> variables -> the measurement type.
WITH 'Pressure' AS measurement_type
MATCH path = (:Pilot)-[:HAS_DATASET]->(:Dataset)-[:HAS_VARIABLE]->(v:Variable)-[:OF_TYPE]->(:MeasurementType {displayName: measurement_type})
RETURN path
LIMIT 300;
