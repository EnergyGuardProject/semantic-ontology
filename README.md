# EnergyGuard Ontology / Knowledge Graph

This repository contains the Neo4j-based semantic data layer for EnergyGuard. It is used to model, import, explore, and visualize ontology-driven energy data for the semantic enrichment and data harmonisation work.

The project combines OWL ontologies, Neo4j, and saved Cypher queries to support interoperability across EnergyGuard use cases and related energy standards such as CIM, SAREF, SSN/SOSA, OEO, Brick, Haystack, OpenADR, OCCP, OntoWind, and RESPOND.

## What is in this repository

```
├── docker-compose.yaml            the Neo4j instance holding the ontology
├── docs/                          plain-language ontology guide, original design workbook
├── ontology/                      all_pilots.owl (generated, loaded by Neo4j) + base ontology + original per-pilot files
├── pilot_metadata/                pilot metadata workbooks + data-lake mapping (CSV)
├── utils/                         build the ontology file · load it into Neo4j (see utils/README.md)
├── scripts/                       examples: explore, visualise, Cypher queries (see scripts/README.md)
├── runtime/                       what Neo4j uses and writes: plugins, data, logs  (data/logs git-ignored)
├── output/                        what the scripts write: backups, visualisations, logs (git-ignored)
└── archive/                       no longer used: old compose files, scripts, queries, Neo4j data, jars
```

## Purpose

The repository supports the EnergyGuard semantic model and ontology work by:

- studying and reusing standard ontologies and vocabularies
- expanding EnergyGuard-specific classes and properties
- importing ontology content into Neo4j for graph exploration
- contextualising the Data Lake developed in T3
- enabling interoperability with AI energy data models and external data services

## Prerequisites

- Docker and Docker Compose
- A Neo4j client such as the browser UI or Cypher shell
- Python 3.12 if you plan to run the helper scripts

## Run Neo4j

```bash
docker compose up -d                      # container "neo4j-ontology", data in runtime/data
utils/neo4j/reload_ontology.sh          # load the ontology (backup -> reset -> import -> mapping -> validation)
```

- Browser: `http://localhost:7474` · Bolt: `bolt://localhost:7687` · user `neo4j`, password in `docker-compose.yaml`
- Public: `neo4j.energy-guard.eu` (nginx-proxy-manager forwards to the container through the `nginxproxy_energyguard_net`
  network, where it is known as `neo4j`)
- Ports are bound to localhost only. From your own machine: `ssh -L 7474:localhost:7474 -L 7687:localhost:7687 <server>`
- This replaces the former live instance (container `neo4j`, run from `/home/atzortzis/neo4j`, now stopped; its data
  is untouched there). Its earlier compose file from this folder is in `archive/docker-compose.live-old.yaml`.

## Load ontology data

> New to the ontology? Start with the plain-language walkthrough: [docs/ontology-guide.md](docs/ontology-guide.md).

All pilots are imported into Neo4j from **one** generated file: `ontology/all_pilots.owl` (the folder is mounted read-only into Neo4j as `/import`).

```
ontology/all_pilots_base.owl   merged pilot ontologies (classes, properties, sample individuals)
pilot_metadata/*.xlsx          dataset + variable metadata delivered by the pilots
        │
        └─ python3 utils/ontology/build_all_pilots_owl.py   (needs: pip install rdflib openpyxl)
        ▼
ontology/all_pilots.owl        the single file loaded with n10s
```

- `ontology/pilots/` keeps the original per-pilot OWL files for reference; they are not imported.
- Every dataset in the metadata becomes a `dcat:Dataset` linked from its pilot (`hasDataset`);
  every column/signal becomes an `eg:Variable` linked from its dataset (`hasVariable`). Sensor
  tags are matched to the existing measurement individuals, so metadata lands on the same node.
- The pilot metadata is the source of truth: for sensors that exist in both, the metadata's
  name (label + database column), unit and value range replace what the base ontology said.
- For CIEMAT, BER, CEA and CARTIF, base content the metadata does not back is dropped: the
  sensors and sample datasets of the original per-pilot ontologies (they were modelled from one
  sample export each), measurement groups left empty, and references to nodes that exist nowhere.
- Every dataset points to where its data really lives in the data lake (one PostgreSQL database
  per pilot, time series in `public.f_tsdata`, REA tables in `gis`/`cadastre`); every variable to its
  lake `sensor_id`, sensor pattern or column. `utils/ontology/discover_data_lake.py` finds these (read-only,
  connection details from the git-ignored `.env`) and writes `ontology/mappings/dataset_tables.csv`,
  `sensor_map.csv` and the report `output/reports/lake_unmapped_sensors.csv`; the build reads them and never connects itself.
- The build is deterministic: re-running with unchanged inputs gives a byte-identical file.

Workflow:

1. Edit `ontology/all_pilots_base.owl` and/or the workbooks in `pilot_metadata/`, then rebuild.
2. Start Neo4j.
3. Run `utils/cypher/01_import_all_pilots_with_n10s.cypher` on a clean database.
4. Or run `utils/neo4j/reload_ontology.sh`, which does the reset, import (01), mapping (02) and validation (03).

## Scripts and visualisation

See [utils/README.md](utils/README.md) for rebuild/reload, and [scripts/README.md](scripts/README.md) for examples: Python visualisations for the terminal
(`scripts/visualize/`, output in `output/visualizations/`) and Cypher queries for the Neo4j Browser
(`scripts/cypher/browser/`, with a Browser style file).

Reload the live graph after a rebuild:

```bash
python3 utils/ontology/build_all_pilots_owl.py
utils/neo4j/reload_ontology.sh            # backup -> reset -> import -> mapping -> validation
neo4j-venv/bin/python scripts/visualize/make_all.py
```

## Notes

- `.gitignore` excludes the container state (`runtime/data`, `runtime/logs`), generated `output/`, the venv and the large parts of `archive/`.
- The repository is focused on the ontology and graph layer rather than application code.

## License

Add the appropriate license for the project if one is required.