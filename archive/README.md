# Archive

Things that are no longer used by the current setup, kept in one place in case they are needed again.
Nothing in the project reads from this folder.

| Folder / file | What it was |
|---|---|
| `runtime_old/data`, `runtime_old/logs` | Neo4j data/logs of this folder's `docker-compose.yaml` before the reorganisation (April 2026 graph). The former live instance ran from `/home/atzortzis/neo4j`. *(git-ignored)* |
| `runtime_old/data-test`, `runtime_old/logs-test` | Data/logs of the old `neo4j-test` instance (`docker-compose.all.yaml`). *(git-ignored)* |
| `runtime_old/plugins-enterprise`, `runtime_old/certificates` | Enterprise APOC jar and HTTPS certificates, not mounted by any compose file. *(git-ignored)* |
| `neosemantics-5.18.0.jar` | Old n10s jar; `runtime/plugins/` has 5.26. *(git-ignored)* |
| `lib/` | JavaScript for the first HTML visualisations. *(git-ignored)* |
| `ciemat-2025-12-04T13-49-14.dump` | A Neo4j dump from the earlier single-pilot (CIEMAT) work, formerly in `import/`. |
| `docker-compose.all.yaml` | Compose file of the old `neo4j-test` instance. |
| `docker-compose.live-old.yaml` | This folder's former compose file for the live `neo4j` instance (network `nginxproxy_energyguard_net`, ports 7474/7687, data in `runtime_old/data`). The live container actually runs from `/home/atzortzis/neo4j`. |
| `scripts_legacy/` | First helper scripts (connection test, CSV cleaning, early visualisations) and their HTML/GraphML outputs. |
| `queries_old/` | Cypher written for the earlier per-pilot graphs (`ns0__` labels, `WindSeries`, Windows file paths) and the Browser export of Nov 2025. |

The Neo4j data folders are owned by the container user (uid 7474). To delete them later:

```bash
docker run --rm -v "$PWD/archive:/a" --entrypoint bash neo4j:2025.10.1-bullseye -c 'rm -rf /a/runtime_old/data /a/runtime_old/logs /a/runtime_old/data-test /a/runtime_old/logs-test'
```
