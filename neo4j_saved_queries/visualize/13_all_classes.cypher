// 13 · The full class hierarchy: shared eg: classes, pilot-specific classes and the pilot tree
// Every class with what it specialises (rdfs:subClassOf). External standard classes
// (SOSA, SAREF, DCAT, ...) appear as the tops of the trees. View: graph.
MATCH path = (c:OntologyClass)-[:rdfs__subClassOf]->(:Resource)
WHERE c.uri STARTS WITH 'https://www.energyguard.eu/ontology'
RETURN path;
