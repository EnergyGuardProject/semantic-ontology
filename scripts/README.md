# Scripts (examples)

Things to **try and learn from**. Nothing here is needed to build or load the graph; that lives in [`utils/`](../utils/README.md).

```
scripts/
├── explore/       STANDALONE kit to let someone test the Neo4j from Python (copy the folder anywhere)
├── visualize/     look at the structure                      (Python, terminal → HTML)
└── cypher/
    ├── browser/   queries to paste into the Neo4j Browser
    └── inspect/   generic checks: schema, labels, all nodes, n10s installed
```

All Python scripts run with the project venv: `neo4j-venv/bin/python …` (it has `neo4j`, `pyvis`, `networkx`).
They connect to the project's Neo4j (`docker-compose.yaml`: `bolt://localhost:7687`, user `neo4j`). Use `--uri` or
set `NEO4J_URI` / `NEO4J_PASSWORD` for another instance.

**Credentials and private inputs are not in git:**
- `.env` (copy `.env.example`) holds `NEO4J_PASSWORD` and the data-lake connection (`DATALAKE_HOST`, `DATALAKE_PORT`,
  `DATALAKE_USER`, `DATALAKE_PASSWORD`). Docker Compose and the scripts read it.
- `pilot_metadata/` holds the partners' metadata workbooks. It is needed only to **rebuild** the ontology;
  loading and querying use the committed `ontology/all_pilots.owl`.
- `ontology/mappings/` (in git) holds where each dataset/variable lives in the lake; reports go to `output/reports/`.

---

## Explore from Python (no Cypher)

[`scripts/explore/`](explore/) is a **standalone kit** to hand to someone who should try the deployed Neo4j: a notebook,
a helper (`eg.py`), `requirements.txt` and its own README. It depends on nothing else in this repository (copy the
folder anywhere); the person only needs the Neo4j address and password.

---

## 1. Visualise in the terminal / browser (Python)

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

## 2. Visualise in the Neo4j Browser (Cypher)

Open the Browser (`http://localhost:7474`, or `neo4j.energy-guard.eu`), paste a query from
`scripts/cypher/browser/` and run it. Queries with a value on the first line (`WITH 'CEA' AS pilot`)
are meant to be edited.

| File | Shows | View |
|---|---|---|
| `00_one_example_path.cypher` | **Start here**: one sensor and everything it connects to (pilot, dataset, class, unit, group) | graph |
| `11_hierarchy_overview.cypher` | **The whole hierarchy at a glance**: pilots → all datasets → 3 example variables each → class → `eg:Measurement`, with units and groups (like the guide's diagram) | graph |
| `12_all_groups.cypher` | All sensor groups, attached to their pilot's datasets | graph |
| `13_all_classes.cypher` | The full class hierarchy: shared `eg:` classes, pilot-specific classes, the pilot tree | graph |
| `14_hierarchy_table.cypher` | The hierarchy as a table: pilot · dataset · variables · kinds of measurement · groups | table |
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

**Nicer colours and captions:** in the Browser type `:style`, then drag `scripts/cypher/browser/browser_style.grass`
onto the style panel (or paste its content). Pilots, datasets, variables, groups and classes get their own colour and
show their name.

---

## Archive

Old scripts, queries and Neo4j data that are no longer used live in [`archive/`](../archive/) (see its README).
