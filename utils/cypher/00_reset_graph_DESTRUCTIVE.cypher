// Name: Reset the graph (DESTRUCTIVE)
// Purpose: Empty the database so 01_import_all_pilots_with_n10s.cypher can load the ontology cleanly.
// Deletes ALL nodes and relationships, the n10s graph config and the n10s prefixes.
// Back up first:  neo4j-venv/bin/python utils/neo4j/backup_graph.py
// Normally run through utils/neo4j/reload_ontology.sh, not by hand.

// 1) delete everything, in batches
MATCH (n)
CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS;

// 2) forget the previous n10s import settings and prefixes (01 sets them again)
CALL n10s.graphconfig.drop();
CALL n10s.nsprefixes.removeAll();

// 3) check
MATCH (n) RETURN count(n) AS nodes_left;
