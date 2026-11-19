# Scripts (examples)

Things to **try and learn from**. Nothing here is needed to build or load the graph; that lives in [`utils/`](../utils/README.md).

```
scripts/
├── explore/       STANDALONE kit to let someone test the Neo4j from Python (copy the folder anywhere)
└── cypher/        queries to paste into the Neo4j Browser (+ browser_style.grass)
```

The explore kit connects to the project's Neo4j (`docker-compose.yaml`: `bolt://localhost:7687`, user `neo4j`). Set `NEO4J_URI` / `NEO4J_PASSWORD` for another instance.

**Credentials and private inputs are not in git:**
- `.env` (copy `.env.example`) holds `NEO4J_PASSWORD`; Docker Compose and `utils/neo4j/reload_ontology.sh` read it. It also has
  optional `DATALAKE_*` settings, used only by the archived `archive/lake_discovery/discover_data_lake.py`.
- Loading and querying use the committed `ontology/all_pilots.owl` (assembled from `ontology/core.ttl` and
  `ontology/catalogue/*.ttl`); partners' Excel files are not needed.

---

## Explore from Python (no Cypher)

[`scripts/explore/`](explore/) is a **standalone kit** to hand to someone who should try the deployed Neo4j: a notebook,
a helper (`eg.py`), `requirements.txt` and its own README. It depends on nothing else in this repository (copy the
folder anywhere); the person only needs the Neo4j address and password.

---

## Saved queries for the Neo4j Browser (Cypher)

Open the Browser (`http://localhost:7474`, or `neo4j.energy-guard.eu`), paste a query from
`scripts/cypher/` and run it. Queries with a value on the first line (`WITH 'CEA' AS pilot`)
are meant to be edited.

| File | Shows | View |
|---|---|---|
| `00_one_example_path.cypher` | **Start here**: one sensor and everything it connects to (pilot, dataset, measurement type, unit, equipment) | graph |
| `01_where_is_the_data.cypher` | Every dataset's data-lake database/table and coverage | table |
| `02_find_a_variable.cypher` | Search a variable → description, unit, and a ready-to-run **SQL** query for its data | table |
| `03_not_in_the_lake.cypher` | Metadata variables not found in the data lake | table |

**Nicer colours and captions:** in the Browser type `:style`, then drag `scripts/cypher/browser_style.grass`
onto the style panel (or paste its content). Pilots, datasets, variables, measurement types, equipment and units get their own colour and
show their name.

---

## Archive

Old generator, vocabularies and Neo4j data that are no longer used live in [`archive/`](../archive/) (see its README).
