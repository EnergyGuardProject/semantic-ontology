// 03 · Variables described in the metadata but not found in the data lake, per pilot
// View: table.
MATCH (p:Pilot)-[:HAS_DATASET]->(d:Dataset)-[:HAS_VARIABLE]->(v:Variable)
WHERE v.lakeMatch = 'none'
RETURN p.displayName AS pilot, d.displayName AS dataset, count(DISTINCT v) AS missing,
       collect(DISTINCT v.displayName)[0..12] AS examples
ORDER BY pilot, missing DESC;
