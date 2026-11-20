# Archive

Things that are no longer used by the current setup, kept in one place in case they are needed again.
Nothing in the project reads from this folder.

| Folder / file | What it was |
|---|---|
| `runtime_old/data`, `runtime_old/logs` | Neo4j data/logs of this folder's `docker-compose.yaml` before the reorganisation (April 2026 graph). The former live instance ran from `/home/atzortzis/neo4j`. *(git-ignored)* |
| `runtime_old/data-test`, `runtime_old/logs-test` | Data/logs of the old `neo4j-test` instance (`docker-compose.all.yaml`). *(git-ignored)* |
| `runtime_old/plugins-enterprise`, `runtime_old/certificates` | Enterprise APOC jar and HTTPS certificates, not mounted by any compose file. *(git-ignored)* |
| `neosemantics-5.18.0.jar` | Old n10s jar; `runtime/plugins/` has 5.26. *(git-ignored)* |
| `ontology_generator/` | `build_all_pilots_owl.py`, the previous generator (Excel workbooks → OWL). Not run any more: `utils/ontology/workbook_diff.py` imports its workbook readers. The rest of the old generator, the pilots' original vocabularies and the old mapping files were deleted; they are in git history. |
| `lake_discovery/` | `discover_data_lake.py`: read-only check of the data lake that proposed where each variable lives. Needs the lake connection in `.env`. Not part of the current workflow. |
| `lib/` | JavaScript for the first HTML visualisations. *(git-ignored)* |

The Neo4j data folders are owned by the container user (uid 7474). To delete them later:

```bash
docker run --rm -v "$PWD/archive:/a" --entrypoint bash neo4j:2025.10.1-bullseye -c 'rm -rf /a/runtime_old/data /a/runtime_old/logs /a/runtime_old/data-test /a/runtime_old/logs-test'
```
