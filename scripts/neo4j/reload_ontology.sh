#!/usr/bin/env bash
# Replace the graph in a Neo4j container with ontology/all_pilots.owl and map it.
#
#   scripts/neo4j/reload_ontology.sh                    # container "neo4j-ontology" (docker-compose.yaml)
#   scripts/neo4j/reload_ontology.sh <other-container>  # any other Neo4j container with n10s + APOC
#
# Steps: backup (JSON) -> reset -> 01 import -> 02 mapping -> 03 validation.
# Password: NEO4J_PASSWORD from the environment, else from the git-ignored .env at the repo root.
set -euo pipefail
cd "$(dirname "$0")/../.."

CONTAINER="${1:-neo4j-ontology}"
PASSWORD="${NEO4J_PASSWORD:-$(sed -n 's/^NEO4J_PASSWORD=//p' .env 2>/dev/null)}"
[ -n "$PASSWORD" ] || { echo "NEO4J_PASSWORD is not set (environment or .env)" >&2; exit 1; }
Q=neo4j_saved_queries/all_pilots
mkdir -p output/logs
LOG="output/logs/reload-${CONTAINER}.txt"

docker ps --format '{{.Names}}' | grep -qx "$CONTAINER" || { echo "container $CONTAINER is not running"; exit 1; }
PORT=$(docker port "$CONTAINER" 7687/tcp | head -1 | sed 's/.*://')
cypher() { docker exec -i "$CONTAINER" cypher-shell -u neo4j -p "$PASSWORD" --format plain; }

echo "== 1/5 backup ($CONTAINER, bolt port $PORT)"
NEO4J_URI="bolt://localhost:$PORT" NEO4J_PASSWORD="$PASSWORD" neo4j-venv/bin/python scripts/neo4j/backup_graph.py --name "$CONTAINER"

echo "== 2/5 reset"
# statement by statement: graphconfig.drop / nsprefixes.removeAll fail harmlessly on a fresh database
: > "$LOG"
cypher <<< "MATCH (n) CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS;" >> "$LOG" 2>&1
cypher <<< "CALL n10s.graphconfig.drop();" >> "$LOG" 2>&1 || true
cypher <<< "CALL n10s.nsprefixes.removeAll();" >> "$LOG" 2>&1 || true
cypher <<< "MATCH (n) RETURN count(n) AS nodes_left;" | tail -1 | sed 's/^/nodes left: /'

echo "== 3/5 import ontology/all_pilots.owl"
# another container may mount a different folder as /import: copy the freshly built file there
IMPORT_DIR=$(docker inspect "$CONTAINER" --format '{{range .Mounts}}{{if eq .Destination "/import"}}{{.Source}}{{end}}{{end}}')
if [ -n "$IMPORT_DIR" ] && [ "$(realpath "$IMPORT_DIR")" != "$(realpath ontology)" ]; then
  cp ontology/all_pilots.owl "$IMPORT_DIR/all_pilots.owl"
  echo "copied ontology/all_pilots.owl -> $IMPORT_DIR/"
fi
cypher < "$Q/01_import_all_pilots_with_n10s.cypher" >> "$LOG" 2>&1
grep -A1 "^terminationStatus" "$LOG" | tail -1 | cut -d, -f1-3 | sed 's/^/status, triples loaded, parsed: /'
grep -q '^"OK"' "$LOG" || { echo "import failed, see $LOG"; exit 1; }

echo "== 4/5 mapping"
cypher < "$Q/02_map_all_pilots_all_in_one.cypher" >> "$LOG" 2>&1
tail -2 "$LOG"

echo "== 5/5 validation"
cypher < "$Q/03_post_import_validation_large_owl.cypher" >> "$LOG" 2>&1
sed -n '/^pilot, located_by/,/^pilot, datasets_not_in_lake/p' "$LOG" | sed '$d'
echo "done (full log: $LOG)"
