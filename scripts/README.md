# Scripts

```
scripts/
├── ontology/      build the ontology file            (Python, terminal)
├── neo4j/         back up and (re)load a Neo4j graph  (bash + Python, terminal)
└── visualize/     look at the structure               (Python, terminal → HTML)
neo4j_saved_queries/
├── all_pilots/    00 reset · 01 import · 02 mapping · 03 validation (run by neo4j/reload_ontology.sh)
├── visualize/     queries to paste into the Neo4j Browser
└── utils/         generic helpers: schema, labels, all nodes, n10s check
```

All Python scripts run with the project venv: `neo4j-venv/bin/python …` (it has `neo4j`, `pyvis`, `networkx`).
They connect to the project's Neo4j (`docker-compose.yaml`: `bolt://localhost:7687`, user `neo4j`, password
`REDACTED`). Use `--uri` or set `NEO4J_URI` / `NEO4J_PASSWORD` for another instance.

---

## 1. Rebuild and reload the ontology

```bash
# only when the data lake changed (finds where each dataset/variable lives; read-only)
DATALAKE_PASSWORD=... python3 scripts/ontology/discover_data_lake.py

# build ontology/all_pilots.owl from ontology/all_pilots_base.owl + pilot_metadata/
python3 scripts/ontology/build_all_pilots_owl.py          # needs: pip install rdflib openpyxl

# back up, empty, import, map and validate a Neo4j container
scripts/neo4j/reload_ontology.sh                 # the project's instance (container "neo4j-ontology")
scripts/neo4j/reload_ontology.sh <container>     # any other Neo4j container
```

`reload_ontology.sh` writes a JSON backup to `output/backups/` first, copies the OWL file into the folder the
container mounts as `/import` (only needed for other containers; this project mounts `ontology/`), and logs everything to `output/logs/reload-<container>.txt`.

---

## 2. Visualise in the terminal / browser (Python)

Run with `neo4j-venv/bin/python scripts/visualize/<script>`. Every script prints to the terminal and writes
an HTML page to `output/visualizations/`.

**Understand the graph**

| Command | What you get |
|---|---|
| `structure.py` | **The shape of the graph**: kinds of nodes (Pilot, Dataset, Variable, Measurement class, Unit, Sensor group, …) and how they connect, with counts. Terminal diagram + `structure.html` |
| `structure.py --pilot BER` | The same for one pilot |
| `pilot_map.py` | **What is in it**: pilots → datasets → kinds of measurement ("Temperature ×19"), all pilots on one page. Terminal outline + `pilot_map.html` |
| `pilot_map.py --pilot CEA` | The same for one pilot |
| `query_demo.py` | **How to use it**: six everyday questions, the Cypher query for each and the answer |
| `query_demo.py --sensor PT305 --kind Pressure --topic heating` | The same questions about another sensor / quantity / topic |
| `class_map.py` | Which measurement classes each pilot has: terminal matrix + `class_map.html` |
| `pilot_graph.py --pilot BER [--groups]` / `--all` | Every variable of a pilot as a node, coloured by class |

**Data lake matching**

| Command | What you get |
|---|---|
| `overview.py [--pilot CEA]` | Pilots → datasets with their data-lake location; with `--pilot`, each variable's lake sensor id |
| `lake_coverage.py --html` | How much of each pilot's metadata is in the lake: terminal bars + `lake_coverage.html` |
| `export_graphml.py [--pilot CEA]` | `structure.graphml` for Gephi / yEd |

**Everything at once:** `make_all.py` → `output/visualizations/index.html`.

The HTML files are self-contained (no internet or server needed): copy them to your laptop and open them in a
browser. Scroll to zoom, drag to move, hover a node for details.

---

## 3. Visualise in the Neo4j Browser (Cypher)

Open the Browser (`http://localhost:7474`, or `neo4j.energy-guard.eu`), paste a query from
`neo4j_saved_queries/visualize/` and run it. Queries with a value on the first line (`WITH 'CEA' AS pilot`)
are meant to be edited.

| File | Shows | View |
|---|---|---|
| `00_one_example_path.cypher` | **Start here**: one sensor and everything it connects to (pilot, dataset, class, unit, group) | graph |
| `01_pilot_tree.cypher` | Pilots → 7 pilots → their datasets | graph |
| `02_one_pilot.cypher` | One pilot → datasets → variables | graph |
| `03_dataset_variables_and_classes.cypher` | One dataset, its variables and their measurement class | graph |
| `04_measurement_classes.cypher` | The shared class hierarchy under `eg:Measurement` | graph |
| `05_same_quantity_across_pilots.cypher` | One kind of measurement (e.g. pressure) in every pilot | graph |
| `06_sensor_groups.cypher` | A pilot's sensor groups and their sensors | graph |
| `07_where_is_the_data.cypher` | Every dataset's data-lake database/table and coverage | table |
| `08_find_a_variable.cypher` | Search a variable → description, unit, and a ready-to-run **SQL** query for its data | table |
| `09_not_in_the_lake.cypher` | Metadata variables not found in the data lake | table |
| `10_schema.cypher` | Labels and relationship types of the whole graph | graph |

**Nicer colours and captions:** in the Browser type `:style`, then drag `neo4j_saved_queries/visualize/browser_style.grass`
onto the style panel (or paste its content). Pilots, datasets, variables, groups and classes get their own colour and
show their name.

---

## Archive

Old scripts, queries and Neo4j data that are no longer used live in [`archive/`](../archive/) (see its README).
