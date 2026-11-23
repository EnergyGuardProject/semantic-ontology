// Name: Import all_pilots.owl with neosemantics (Docker/Linux)
// Purpose: One-stop setup + import for /import/all_pilots.owl (= ontology/all_pilots.owl on the host)
// Notes:
// - ontology/all_pilots.owl is the ONE ontology file for all pilots (schema + pilot metadata).
//   It is generated — rebuild it after changing ontology/all_pilots_base.owl or pilot_metadata/*.xlsx:
//     python3 utils/ontology/build_all_pilots_owl.py
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

// 3b) Register prefixes so labels/relationships read e.g. eg__TemperatureMeasurement, dcterms__isPartOf
//     (without this n10s invents ns0__, ns1__, ...; queries in 02 rely on these names)
CALL n10s.nsprefixes.add('eg', 'https://ontology.energy-guard.eu/core#');
CALL n10s.nsprefixes.add('mp', 'https://ontology.energy-guard.eu/pilots#');
CALL n10s.nsprefixes.add('rdn', 'https://ontology.energy-guard.eu/rdn#');
CALL n10s.nsprefixes.add('ciemat', 'https://ontology.energy-guard.eu/ciemat#');
CALL n10s.nsprefixes.add('ber', 'https://ontology.energy-guard.eu/ber#');
CALL n10s.nsprefixes.add('cea', 'https://ontology.energy-guard.eu/cea#');
CALL n10s.nsprefixes.add('cartif', 'https://ontology.energy-guard.eu/cartif#');
CALL n10s.nsprefixes.add('rea', 'https://ontology.energy-guard.eu/rea#');
CALL n10s.nsprefixes.add('engreen', 'https://ontology.energy-guard.eu/engreen#');
// standard vocabularies used by the ontology
CALL n10s.nsprefixes.add('dcterms', 'http://purl.org/dc/terms/');
CALL n10s.nsprefixes.add('dcat', 'http://www.w3.org/ns/dcat#');
CALL n10s.nsprefixes.add('sosa', 'http://www.w3.org/ns/sosa/');
CALL n10s.nsprefixes.add('saref', 'https://saref.etsi.org/core/');
CALL n10s.nsprefixes.add('s4ener', 'https://saref.etsi.org/saref4ener/');
CALL n10s.nsprefixes.add('qudt', 'http://qudt.org/schema/qudt/');
CALL n10s.nsprefixes.add('unit', 'http://qudt.org/vocab/unit/');
CALL n10s.nsprefixes.add('qb', 'http://purl.org/linked-data/cube#');
CALL n10s.nsprefixes.add('bot', 'https://w3id.org/bot#');
CALL n10s.nsprefixes.add('foaf', 'http://xmlns.com/foaf/0.1/');
CALL n10s.nsprefixes.add('geo', 'http://www.w3.org/2003/01/geo/wgs84_pos#');
CALL n10s.nsprefixes.add('vann', 'http://purl.org/vocab/vann/');
CALL n10s.nsprefixes.add('xsd', 'http://www.w3.org/2001/XMLSchema#');
CALL n10s.nsprefixes.add('skos', 'http://www.w3.org/2004/02/skos/core#');
CALL n10s.nsprefixes.add('prov', 'http://www.w3.org/ns/prov#');
CALL n10s.nsprefixes.add('dqv', 'http://www.w3.org/ns/dqv#');
CALL n10s.nsprefixes.add('vcard', 'http://www.w3.org/2006/vcard/ns#');
CALL n10s.nsprefixes.add('geosparql', 'http://www.opengis.net/ont/geosparql#');
CALL n10s.nsprefixes.add('quantitykind', 'http://qudt.org/vocab/quantitykind/');
CALL n10s.nsprefixes.add('prop', 'https://ontology.energy-guard.eu/property#');
CALL n10s.nsprefixes.add('csvw', 'http://www.w3.org/ns/csvw#');

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

// 6) Pilot metadata: datasets and variables per pilot (suffix-free: uses the standard dct:publisher link)
MATCH (ds:dcat__Dataset)-[:dcterms__publisher]->(p:Resource)
OPTIONAL MATCH (ds)-[:sch__variableMeasured]->(var:Resource)
RETURN p.rdfs__label AS pilot,
       count(DISTINCT ds) AS datasets,
       count(DISTINCT var) AS variables
ORDER BY pilot;
