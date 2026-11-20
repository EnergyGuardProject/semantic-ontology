// 12 · The catalogue (dcat:Catalog) with its datasets, and each dataset's pilot
// View: graph. One catalogue node in the middle, 41 datasets around it, pilots behind them.
MATCH cat = (:dcat__Catalog)-[:dcat__dataset]->(d:Dataset)
OPTIONAL MATCH pilot = (:Pilot)-[:HAS_DATASET]->(d)
RETURN cat, pilot;
