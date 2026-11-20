# Utils (build and load the graph)

What the Neo4j graph **depends on**. These are not examples: run them to build `ontology/all_pilots.owl` and load it.
For things to try, see [`scripts/`](../scripts/README.md).

```
utils/
├── ontology/   assemble and validate the ontology file (Python, terminal)
├── neo4j/      (re)load a Neo4j graph                  (bash, terminal)
└── cypher/     01 import · 02 mapping (run by neo4j/reload_ontology.sh)
```

The `ontology/` scripts need `rdflib` (`assemble.py`, `workbook_diff.py`, which also needs `openpyxl`) and `pyshacl` (`validate_shapes.py`). Credentials (`.env`) are not in git: see [`scripts/README.md`](../scripts/README.md) and `.env.example`.

---

## Rebuild and reload the ontology

```bash
# edit the hand-written sources: ontology/core.ttl and ontology/catalogue/*.ttl, then
python3 utils/ontology/assemble.py            # -> ontology/all_pilots.owl   (needs: pip install rdflib)
python3 utils/ontology/validate_shapes.py     # SHACL checks against ontology/shapes.ttl (needs: pip install pyshacl)

# when a partner sends a new workbook: report what it would change (applies nothing)
python3 utils/ontology/workbook_diff.py <pilot>

# empty, import and map a Neo4j container
utils/neo4j/reload_ontology.sh                 # the project's instance (container "neo4j-ontology")
utils/neo4j/reload_ontology.sh <container>     # any other Neo4j container
```

`reload_ontology.sh` empties the graph, imports the file and maps it (the graph is generated, so nothing is backed up). It copies the OWL file into the folder the
container mounts as `/import` (only needed for other containers; this project mounts `ontology/`), and logs everything to `output/logs/reload-<container>.txt`.

