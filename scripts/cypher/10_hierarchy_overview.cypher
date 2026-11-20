// 10 · The whole hierarchy at a glance (like the diagram in docs/ontology-guide.md)
// Pilots -> every dataset -> up to 3 example variables per dataset -> their measurement type and unit.
// View: graph. Tip: load browser_style.grass first (:style) for colours and names.
// Change the 3 below to show more or fewer variables per dataset.
MATCH ds = (:Pilot)-[:HAS_DATASET]->(d:Dataset)
CALL (d) {
  OPTIONAL MATCH (d)-[:HAS_VARIABLE]->(v:Variable)
  WITH v ORDER BY v.displayName
  LIMIT 3
  OPTIONAL MATCH vp = (d)-[:HAS_VARIABLE]->(v)
  OPTIONAL MATCH ty = (v)-[:OF_TYPE]->(:MeasurementType)
  OPTIONAL MATCH unit = (v)-[:HAS_UNIT]->(:Unit)
  RETURN collect(vp) AS variables, collect(ty) AS types, collect(unit) AS units
}
RETURN ds, variables, types, units;
