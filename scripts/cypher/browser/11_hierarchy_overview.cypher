// 11 · The whole hierarchy at a glance (like the diagram in docs/ontology-guide.md)
// Pilots -> pilots (+ sub-pilots) -> every dataset -> up to 3 example variables per dataset
//        -> their measurement class -> eg:Measurement, plus each variable's unit and sensor group.
// View: graph. Tip: load browser_style.grass first (:style) for colours and names.
// Change the 3 below to show more or fewer variables per dataset.
MATCH tree = (:Resource {uri: 'https://www.energyguard.eu/ontology/merged-pilots#Pilots'})-[:mp__hasPilot]->(p:Pilot)
OPTIONAL MATCH sub = (p)-[:mp__hasSubPilot]->(:SubPilot)
OPTIONAL MATCH ds = (p)-[:mp__hasDataset]->(d:Dataset)
CALL (d) {
  OPTIONAL MATCH (d)-[:eg__hasVariable]->(m:Measurement)
  WITH m ORDER BY EXISTS { (m)-[:INSTANCE_OF]->() } DESC, m.displayName
  LIMIT 3
  OPTIONAL MATCH v = (d)-[:eg__hasVariable]->(m)
  OPTIONAL MATCH cls = (m)-[:INSTANCE_OF]->(:OntologyClass)-[:rdfs__subClassOf]->(:OntologyClass)
  OPTIONAL MATCH unit = (m)-[:eg__hasUnit]->()
  OPTIONAL MATCH grp = (m)<-[:eg__hasMeasurement]-(:MeasurementGroup)
  RETURN collect(v) AS variables, collect(cls) AS classes, collect(unit) AS units, collect(grp) AS groups
}
RETURN tree, sub, ds, variables, classes, units, groups;
