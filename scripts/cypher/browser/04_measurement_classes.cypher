// 04 · The shared measurement classes: eg:Measurement and its sub-classes
// View: graph. Every class points to the class it specialises.
MATCH path = (:OntologyClass)-[:rdfs__subClassOf*1..3]->(m:OntologyClass {uri: 'https://www.energyguard.eu/ontology#Measurement'})
RETURN path;
