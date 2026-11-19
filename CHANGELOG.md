# Changelog

## 2.0.0

Rebuilt on standards; the ontology is now hand-curated Turtle instead of generated from the partners' workbooks.

- **Standards first:** datasets are `dcat:Dataset`; sensors, equipment and measurement types are SOSA; units and quantity kinds are QUDT; measurement types are a SKOS scheme; provenance and quality use PROV and DQV; SHACL checks added (`ontology/shapes.ttl`).
- **Removed:** the pilots' own vocabularies (measurement classes, sensor groups, ~85 unused properties). They are kept in `archive/pilot_ontologies/`.
- **Source of truth:** `ontology/core.ttl` (19 EnergyGuard terms) and `ontology/catalogue/*.ttl`. `utils/ontology/assemble.py` builds `ontology/all_pilots.owl`. Workbooks are compared with `workbook_diff.py` and never applied automatically.
- **Valid ranges:** 82 clean numeric ranges are now `schema:minValue` / `schema:maxValue`; qualified ranges ("approx.", lists, one-sided) stay as `skos:note`.
- **Data lake links:** `eg:LakeLink` removed. An inferred match is `eg:dataLakeMatch "inferred"` plus the reason in `eg:dataLakeEvidence`.
- **Descriptions:** the 17 datasets the pilots did not describe (12 REA, 5 RDN) got a stated-as-derived description.
- **More standard terms:** `eg:hasVariable` → `schema:variableMeasured`, `eg:unit` → `schema:unitText`, `eg:fileFormat` → `dct:format`, `eg:missingValues` → `csvw:null`. Valid ranges and decimals are now typed numbers (`xsd:decimal`, `xsd:integer`); `2^32` became 4294967296. In Neo4j the dataset-to-variable edge is `HAS_VARIABLE`.
- **Trimmed:** `eg:TimeColumn` and `eg:IdentifierColumn` became `variableKind` values (`timestamp`, `identifier`); `eg:systemDescribed` and `eg:sourceSystem` were folded into the dataset description; `eg:recordCount` was dropped. 19 EnergyGuard terms remain.
- **Catalogue:** one `dcat:Catalog` (`mp:EnergyGuardCatalogue`) lists all 41 datasets and the data lake service.
- **Language:** every description is English; the 90 extra Spanish copies (CARTIF) were dropped (the workbook still has them).
- **Neo4j:** labels Pilot, Dataset, Variable, MeasurementType, Platform, Unit; edges HAS_DATASET, OF_TYPE, HAS_UNIT, HOSTED_BY. The old `BELONGS_TO_DATASET` edge and per-variable database shortcuts were removed.

## 1.0.0

First generated version (per-pilot vocabularies merged with the workbook metadata).
