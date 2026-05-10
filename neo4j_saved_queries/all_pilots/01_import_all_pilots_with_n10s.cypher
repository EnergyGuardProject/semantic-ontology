// Name: Import all_pilots.owl with neosemantics (Docker/Linux)
// Purpose: One-stop setup + import for /import/all_pilots.owl
// Notes:
// - Run on a clean graph if this is a fresh ontology load.
// - Your docker-compose mounts ./import to Neo4j /import, so file:///import/all_pilots.owl is the correct container path.

// 1) Validate n10s procedures exist
SHOW PROCEDURES YIELD name
WHERE name STARTS WITH 'n10s'
RETURN name
ORDER BY name;

// 2) Uniqueness constraint required by n10s best practice
CREATE CONSTRAINT n10s_unique_uri IF NOT EXISTS
FOR (r:Resource)
REQUIRE r.uri IS UNIQUE;

// 3) Initialize graph config (safe defaults for this ontology)
// If already initialized, Neo4j will return an error. In that case, run:
// CALL n10s.graphconfig.show();
// and keep existing config, or clear DB and init again.
CALL n10s.graphconfig.init({
  handleVocabUris: 'SHORTEN',
  typesToLabels: true,
  handleMultival: 'ARRAY',
  keepCustomDataTypes: true
});

// 4) Import OWL from Neo4j import directory
CALL n10s.rdf.import.fetch(
  'file:///import/all_pilots.owl',
  'RDF/XML'
);

// 5) Quick sanity checks
MATCH (n:Resource)
RETURN count(n) AS resource_nodes;

MATCH ()-[r]->()
RETURN count(r) AS relationships;
