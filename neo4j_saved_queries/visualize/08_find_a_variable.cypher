// 08 · Find a variable and get a ready-to-run SQL query for its data
// Edit the search text (part of the name, case-insensitive). View: table.
// Run the `sql` column in the pilot's database (e.g. in pgAdmin on TEF3_BER).
WITH toLower('TT-D101') AS q
MATCH (p:Pilot)-[:mp__hasDataset]->(d:Dataset)-[:eg__hasVariable]->(v:Measurement)
WHERE toLower(v.displayName) CONTAINS q
WITH p, d, v, d.eg__storedInDatabase[0] AS db, d.eg__tableLayout[0] AS layout
RETURN p.displayName AS pilot, d.displayName AS dataset, v.displayName AS variable,
       v.measurementType AS class, v.eg__unit[0] AS unit, v.dcterms__description[0] AS description,
       db AS database, v.lakeMatch AS found_by,
       CASE
         WHEN v.lakeSensorId IS NOT NULL THEN
           "SELECT c.datetime, f.f_value FROM public.f_tsdata f JOIN public.d_calendar c USING (calendar_id) WHERE f.sensor_id = '" + v.lakeSensorId + "' ORDER BY f.calendar_id DESC LIMIT 100;"
         WHEN v.lakeSensorPattern IS NOT NULL THEN
           "SELECT f.sensor_id, c.datetime, f.f_value FROM public.f_tsdata f JOIN public.d_calendar c USING (calendar_id) WHERE f.sensor_id LIKE '" + v.lakeSensorPattern + "' ORDER BY f.calendar_id DESC LIMIT 100;"
         WHEN layout = 'wide' AND v.lakeColumn IS NOT NULL THEN
           "SELECT " + v.lakeColumn + " FROM " + d.eg__storedInDatabaseTable[0] + " LIMIT 100;"
         ELSE '— not in the data lake'
       END AS sql
ORDER BY pilot, dataset
LIMIT 50;
