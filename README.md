# EnergyGuard Ontology / Knowledge Graph

This repository contains the Neo4j-based semantic data layer for EnergyGuard. It is used to model, import, and explore ontology-driven energy data for the semantic enrichment and data harmonisation work.

The ontology is a **catalogue** of the pilots' datasets and variables and where each is stored in the data lake. It reuses standards (DCAT, SOSA, QUDT, SKOS, SHACL) and adds about 13 terms of its own. Version 2.0.0, see [CHANGELOG.md](CHANGELOG.md).

## What is in this repository

```
├── docker-compose.yaml            the Neo4j instance holding the ontology
├── docs/                          plain-language ontology guide, original design workbook
├── CHANGELOG.md                   what changed between ontology versions
├── ontology/                      core.ttl + catalogue/*.ttl (hand-written) + shapes.ttl; all_pilots.owl is assembled from them
├── utils/                         build the ontology file · load it into Neo4j (see utils/README.md)
├── scripts/                       examples: explore kit (Python), saved Cypher queries (see scripts/README.md)
├── runtime/                       what Neo4j uses and writes: plugins, data, logs  (data/logs git-ignored)
├── output/                        what the scripts write: logs (git-ignored)
└── archive/                       no longer used: the old generator, pilots' vocabularies, Neo4j data, jars
```

## Purpose

The repository supports the EnergyGuard semantic model and ontology work by:

- reusing standard ontologies and vocabularies wherever one fits
- keeping the few EnergyGuard-specific terms small and documented
- importing ontology content into Neo4j for graph exploration
- contextualising the Data Lake developed in T3
- enabling interoperability with AI energy data models and external data services

## Prerequisites

- Docker and Docker Compose
- A Neo4j client such as the browser UI or Cypher shell
- Python 3.12 for `utils/ontology/` (`pip install rdflib pyshacl openpyxl`) and the explore kit (see its README)

## Run Neo4j

```bash
docker compose up -d                      # container "neo4j-ontology", data in runtime/data
utils/neo4j/reload_ontology.sh          # load the ontology (reset -> import -> mapping)
```

- Browser: `http://localhost:7474` · Bolt: `bolt://localhost:7687` · user `neo4j`, password in `docker-compose.yaml`
- Public: `neo4j.energy-guard.eu` (nginx-proxy-manager forwards to the container through the `nginxproxy_energyguard_net`
  network, where it is known as `neo4j`)
- Ports are bound to localhost only. From your own machine: `ssh -L 7474:localhost:7474 -L 7687:localhost:7687 <server>`
- This replaces the former live instance (container `neo4j`, run from `/home/atzortzis/neo4j`, now stopped; its data
  is untouched there).

## Load ontology data

> New to the ontology? Start with the plain-language walkthrough: [docs/ontology-guide.md](docs/ontology-guide.md).

The ontology is written by hand in Turtle (`ontology/core.ttl`, `ontology/catalogue/*.ttl`, checks in
`ontology/shapes.ttl`) and assembled into **one** file, `ontology/all_pilots.owl`, which Neo4j imports (the `ontology/`
folder is mounted read-only into Neo4j as `/import`). The partners' Excel workbooks are reference material: nothing reads
them automatically. See the guide, section 6, for the details.

After editing the Turtle files:

```bash
python3 utils/ontology/assemble.py            # build all_pilots.owl   (needs: pip install rdflib)
python3 utils/ontology/validate_shapes.py     # SHACL checks            (needs: pip install pyshacl)
utils/neo4j/reload_ontology.sh                # reset -> import -> mapping
```

More: [utils/README.md](utils/README.md) (assemble, validate, reload) and [scripts/README.md](scripts/README.md) (the
explore kit, which needs no Cypher, and the 13 saved queries for the Neo4j Browser).

## Notes

- `.gitignore` excludes the container state (`runtime/data`, `runtime/logs`), `output/`, the venv and the large parts of `archive/`.
- The repository is focused on the ontology and graph layer rather than application code.

## License

The ontology is declared GPL-3.0 in its header (`ontology/core.ttl`).