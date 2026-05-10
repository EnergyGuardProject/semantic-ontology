// Name: Safer staged import for large ontology loads
// Purpose: Import pilot OWL files one by one (smaller transactions, easier recovery).
// Use this if full all_pilots.owl import is too heavy or times out.

// Assumes n10s is already initialized and n10s_unique_uri constraint exists.
// If you need setup, run:
// neo4j_saved_queries/all_pilots/01_import_all_pilots_with_n10s.cypher

// Optional: inspect current graph config
CALL n10s.graphconfig.show();

// Import each available OWL source file in sequence
CALL n10s.rdf.import.fetch('file:///pilot1_f.owl', 'RDF/XML');
CALL n10s.rdf.import.fetch('file:///pilot1_ts.owl', 'RDF/XML');
CALL n10s.rdf.import.fetch('file:///pilot2.owl', 'RDF/XML');
CALL n10s.rdf.import.fetch('file:///pilot3_ber.owl', 'RDF/XML');
CALL n10s.rdf.import.fetch('file:///pilot3_cartif.owl', 'RDF/XML');
CALL n10s.rdf.import.fetch('file:///pilot3_cea.owl', 'RDF/XML');
CALL n10s.rdf.import.fetch('file:///pilot5_engreen.owl', 'RDF/XML');

// Quick totals
MATCH (n:Resource)
WITH count(n) AS nodes
MATCH ()-[r]->()
RETURN nodes, count(r) AS rels;
