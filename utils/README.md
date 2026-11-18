# Utils (build and load the graph)

What the Neo4j graph **depends on**. These are not examples: run them to build `ontology/all_pilots.owl` and load it.
For things to try, see [`scripts/`](../scripts/README.md).

```
utils/
├── ontology/   build the ontology file                 (Python, terminal)
├── neo4j/      back up and (re)load a Neo4j graph      (bash + Python, terminal)
└── cypher/     00 reset · 01 import · 02 mapping · 03 validation (run by neo4j/reload_ontology.sh)
```

Python scripts run with the project venv (`neo4j-venv/bin/python …`). Credentials (`.env`) and `pilot_metadata/`
are not in git: see [`scripts/README.md`](../scripts/README.md) and `.env.example`.

---

## Rebuild and reload the ontology

```bash
# only when the data lake changed (finds where each dataset/variable lives; read-only).
# Hand corrections go in ontology/mappings/sensor_map_overrides.csv: they are applied last and win.
python3 utils/ontology/discover_data_lake.py

# build ontology/all_pilots.owl from ontology/all_pilots_base.owl + pilot_metadata/
python3 utils/ontology/build_all_pilots_owl.py          # needs: pip install rdflib openpyxl

# back up, empty, import, map and validate a Neo4j container
utils/neo4j/reload_ontology.sh                 # the project's instance (container "neo4j-ontology")
utils/neo4j/reload_ontology.sh <container>     # any other Neo4j container
```

`reload_ontology.sh` writes a JSON backup to `output/backups/` first, copies the OWL file into the folder the
container mounts as `/import` (only needed for other containers; this project mounts `ontology/`), and logs everything to `output/logs/reload-<container>.txt`.

