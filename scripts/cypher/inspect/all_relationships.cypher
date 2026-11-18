// Name: Return nodes, relationships and other nodes
// Description: (none)
MATCH (n)-[r]-(n2)
RETURN n, r, n2;
