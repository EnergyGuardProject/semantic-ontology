# EnergyGuard Ontology / Knowledge Graph

This repository contains the Neo4j-based semantic data layer for EnergyGuard. It is used to model, import, explore, and visualize ontology-driven energy data for the semantic enrichment and data harmonisation work.

The project combines OWL ontologies, Neo4j, and saved Cypher queries to support interoperability across EnergyGuard use cases and related energy standards such as CIM, SAREF, SSN/SOSA, OEO, Brick, Haystack, OpenADR, OCCP, OntoWind, and RESPOND.

## What is in this repository

- `docker-compose.yaml` for running Neo4j with the required volumes and extensions
- `import/` for OWL ontologies and sample source files
- `neo4j_saved_queries/` for reusable Cypher queries and Neo4j tooling scripts
- `scripts/` for Python utilities such as graph visualization and import checks
- `data/`, `logs/`, and `plugins/` for the local Neo4j runtime

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

## Run Neo4j locally

Start the database with Docker Compose:

```bash
docker compose up -d
```

Neo4j will be available at:

- HTTP: `http://localhost:7474`
- Bolt: `bolt://localhost:7687`

The default credentials in this setup are configured in `docker-compose.yaml`.

## Load ontology data

The repository includes OWL files under `import/` and saved Cypher examples under `neo4j_saved_queries/`.

Common workflow:

1. Start Neo4j.
2. Run the n10s initialization query from `neo4j_saved_queries/n10s_installation/`.
3. Import the desired OWL ontology from the `import/` directory.
4. Explore the graph with the saved query set or your own Cypher queries.

## Visualization helpers

The `scripts/` directory contains small Python utilities for querying Neo4j and rendering graph views, including:

- `scripts/simple_graph_viz.py`
- `scripts/visualize_owl_import.py`

## Notes

- `.gitignore` already excludes local runtime data such as `data/`, `logs/`, `plugins-enterprise/`, `neo4j-venv/`, and `certificates/`.
- The repository is focused on the ontology and graph layer rather than application code.

## License

Add the appropriate license for the project if one is required.