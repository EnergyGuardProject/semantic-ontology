// 07 · Where each dataset lives in the data lake, and how many of its variables are found there
// View: table.
MATCH (p:Pilot)-[:mp__hasDataset]->(d:Dataset)
OPTIONAL MATCH (d)-[:eg__hasVariable]->(v)
WITH p, d, count(v) AS variables, count(CASE WHEN v.lakeMatch <> 'none' THEN 1 END) AS found
RETURN p.displayName AS pilot, d.displayName AS dataset,
       coalesce(d.eg__storedInDatabase[0], '— not in the lake') AS database,
       d.eg__storedInDatabaseTable AS tables, d.eg__tableLayout[0] AS layout,
       variables, found
ORDER BY pilot, dataset;
