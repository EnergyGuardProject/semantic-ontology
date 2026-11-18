// 01 · The pilot tree: Pilots -> 7 pilots -> their datasets (and RDN's two sub-pilots)
// View: graph. Big boxes = pilots, small = datasets.
MATCH p1 = (:Resource {uri: 'https://www.energyguard.eu/ontology/merged-pilots#Pilots'})-[:mp__hasPilot]->(p:Pilot)
OPTIONAL MATCH p2 = (p)-[:mp__hasDataset]->(:Dataset)
OPTIONAL MATCH p3 = (p)-[:mp__hasSubPilot]->(:SubPilot)
RETURN p1, p2, p3;
