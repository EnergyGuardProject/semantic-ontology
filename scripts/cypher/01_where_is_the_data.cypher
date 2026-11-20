// 01 · Where each dataset lives in the data lake, and how many of its variables are found there
// View: table.
MATCH (p:Pilot)-[:HAS_DATASET]->(d:Dataset)
OPTIONAL MATCH (d)-[:HAS_VARIABLE]->(v)
WITH p, d, count(v) AS variables, count(CASE WHEN v.inLake THEN 1 END) AS found
RETURN p.displayName AS pilot, d.displayName AS dataset,
       coalesce(d.database, '— not in the lake') AS database,
       d.dbTables AS tables, d.tableLayout AS layout,
       variables, found
ORDER BY pilot, dataset;
