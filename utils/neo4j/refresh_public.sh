#!/usr/bin/env bash
# Copy the graph of the private instance (neo4j-ontology) into the public one (neo4j-public), read-only.
#
#   utils/neo4j/refresh_public.sh        # run it after every reload of the private graph
#
# The private instance stops for a few seconds while its database is dumped, and is left as it was found: if it was
# stopped it stays stopped, if it was running it is started again. The public instance is rebuilt from the dump each time, so its data, users and password are reset to what docker-compose.yaml and .env say. Anyone who
# changed the shared password (Neo4j Community cannot stop that) is undone by running this script.
set -euo pipefail
cd "$(dirname "$0")/../.."
IMG=neo4j:2025.10.1-bullseye
[ -n "$(sed -n 's/^NEO4J_PUBLIC_PASSWORD=//p' .env 2>/dev/null)" ] || { echo "NEO4J_PUBLIC_PASSWORD is not set in .env" >&2; exit 1; }
mkdir -p output/dump runtime/public-data runtime/public-logs
chmod 777 output/dump runtime/public-logs   # the neo4j user inside the containers writes here

echo "== 1/4 dump the private graph"
WAS_RUNNING=$(docker inspect -f '{{.State.Running}}' neo4j-ontology 2>/dev/null || echo false)
if [ "$WAS_RUNNING" = true ]; then
  docker stop neo4j-ontology >/dev/null
  trap 'docker start neo4j-ontology >/dev/null 2>&1 || true' EXIT
fi
rm -f output/dump/neo4j.dump   # always dump into a fresh file: a dump written over an old one cannot be loaded
docker run --rm -v "$PWD/runtime/data:/data" -v "$PWD/output/dump:/dump" "$IMG" \
  neo4j-admin database dump neo4j --to-path=/dump 2>&1 | tail -2
if [ "$WAS_RUNNING" = true ]; then
  docker start neo4j-ontology >/dev/null
  trap - EXIT
fi

echo "== 2/4 empty the public instance"
docker compose stop neo4j-public >/dev/null 2>&1 || true
docker run --rm --entrypoint bash -v "$PWD/runtime/public-data:/data" "$IMG" -c 'rm -rf /data/* && chown 7474:7474 /data'

echo "== 3/4 load the dump"
docker run --rm -v "$PWD/runtime/public-data:/data" -v "$PWD/output/dump:/dump" "$IMG" \
  neo4j-admin database load neo4j --from-path=/dump --overwrite-destination=true 2>&1 | tail -2

echo "== 4/4 start the public instance (read-only)"
docker compose up -d neo4j-public >/dev/null
echo "done: neo4j-public is starting (http://localhost:7475 from this machine)"
