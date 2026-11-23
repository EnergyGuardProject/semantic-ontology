# Scripts (examples)

Things to **try and learn from**. Nothing here is needed to build or load the graph; that lives in [`utils/`](../utils/README.md).

```
scripts/
├── explore/       STANDALONE kit to let someone test the Neo4j from Python (copy the folder anywhere)
└── cypher/        queries to paste into the Neo4j Browser (+ browser_style.grass)
```

The explore kit connects to the public read-only Neo4j at `https://ontology.energy-guard.eu` (user `neo4j`, the shared password). Set `NEO4J_URI` / `NEO4J_PASSWORD` for another instance, for example `bolt://localhost:7687` on the server.

**Credentials are not in git:**
- `.env` (copy `.env.example`) holds `NEO4J_PASSWORD` (the private instance) and `NEO4J_PUBLIC_PASSWORD` (the shared read-only one); Docker Compose and the scripts in `utils/neo4j/` read it.
- Loading and querying use the committed `ontology/all_pilots.owl` (assembled from `ontology/core.ttl` and
  `ontology/catalogue/*.ttl`); partners' Excel files are not needed.

---

## Explore from Python (no Cypher)

[`scripts/explore/`](explore/) is a **standalone kit** to hand to someone who should try the deployed Neo4j: a notebook,
a helper (`eg.py`), `requirements.txt` and its own README. It depends on nothing else in this repository (copy the
folder anywhere); the person only needs the Neo4j address and password.

---

## Saved queries for the Neo4j Browser (Cypher)

Open the Browser (`http://localhost:7474`, or `https://ontology.energy-guard.eu/browser/`), paste a query from
`scripts/cypher/` and run it. Queries with a value on the first line (`WITH 'CEA' AS pilot`)
are meant to be edited.

| File | Shows | View |
|---|---|---|
| `00_one_example_path.cypher` | **Start here**: one sensor and everything it connects to (pilot, dataset, measurement type, unit, equipment) | graph |
| `01_where_is_the_data.cypher` | Every dataset's data-lake database/table and coverage | table |
| `02_find_a_variable.cypher` | Search a variable → description, unit, and a ready-to-run **SQL** query for its data | table |
| `03_not_in_the_lake.cypher` | Metadata variables not found in the data lake | table |
| `04_pilots_and_datasets.cypher` | The pilots and their datasets | graph |
| `05_one_pilot.cypher` | One pilot → datasets → variables | graph |
| `06_dataset_variables_and_types.cypher` | One dataset, its variables, what each measures and its unit | graph |
| `07_measurement_types.cypher` | The shared measurement types and their QUDT quantity kinds | graph |
| `08_same_measurement_type_across_pilots.cypher` | One measurement type (e.g. pressure) in every pilot | graph |
| `09_equipment.cypher` | A pilot's equipment and the variables it hosts | graph |
| `10_hierarchy_overview.cypher` | **The whole hierarchy at a glance**: pilots → datasets → 3 example variables → type and unit | graph |
| `11_schema.cypher` | Labels and relationships of the whole graph | graph |
| `12_catalogue.cypher` | The catalogue, its datasets and their pilots | graph |

**Nicer colours and captions:** in the Browser type `:style`, then drag `scripts/cypher/browser_style.grass`
onto the style panel (or paste its content). Pilots, datasets, variables, measurement types, equipment and units get their own colour and
show their name.

---

## Archive

Old generator, vocabularies and Neo4j data that are no longer used live in [`archive/`](../archive/) (see its README).
