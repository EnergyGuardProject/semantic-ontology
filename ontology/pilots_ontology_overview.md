# EnergyGuard Pilots – Ontology High-Level Overview

> Historical note on the original per-pilot vocabularies in `ontology/pilots/`. For the current, complete
> structure (pilots → datasets → variables) see [docs/ontology-guide.md](../docs/ontology-guide.md).

---

## RDN (rdn_faults.owl, rdn_timeseries.owl)
- **Domain:** Faults and time series for RDN
- **Key Entities:**
  - Dataset (e.g., timeseries, faults)
  - MeasurementGroup (logical groupings of measurements)
  - Measurement (individual sensor readings, events)
  - Unit (e.g., A, V, °C)
- **Important Relationships:**
  - Dataset → MeasurementGroup (ns0__hasGroup)
  - MeasurementGroup → Measurement (ns0__hasMeasurement)
  - Measurement → Unit (ns0__hasUnit)
- **Structure:**
  - Hierarchical: Dataset → Group → Measurement
  - Rich metadata for each measurement (e.g., code, dbTable)

---

## CIEMAT (ciemat.owl)
- **Domain:** CIEMAT energy and system ontology
- **Key Entities:**
  - Dataset (energy datasets, system logs)
  - MeasurementGroup (system components, logical groups)
  - Measurement (sensor readings, component states)
  - Unit (measurement units)
- **Important Relationships:**
  - Dataset → MeasurementGroup (ns0__hasGroup)
  - MeasurementGroup → Measurement (ns0__hasMeasurement, ns9__hasMeasurement)
  - Measurement → Unit (ns0__hasUnit, ns16__hasUnit)
- **Structure:**
  - Modular, with clear separation of datasets and groups
  - Supports component mapping and system-level analysis

---

## CEA, CARTIF, BER (cea.owl, cartif.owl, ber.owl)
- **Domain:** Three subdomains: CEA, CARTIF, BER
- **Key Entities:**
  - Dataset (per subdomain)
  - MeasurementGroup (subsystem groupings)
  - Measurement (domain-specific sensors, events)
  - Unit (domain-specific units)
- **Important Relationships:**
  - Dataset → MeasurementGroup (ns0__hasGroup)
  - MeasurementGroup → Measurement (ns0__hasMeasurement, ns9__hasMeasurement)
  - Measurement → Unit (ns0__hasUnit, ns16__hasUnit)
- **Structure:**
  - Each subdomain is a self-contained ontology
  - Harmonized structure enables cross-domain queries
  - Labels: CEA, CARTIF, BER

---

## REA (rea.owl)
- **Domain:** REA (Riga Energy Agency), building and energy ontology
- **Key Entities:**
  - Dataset (building datasets)
  - MeasurementGroup (building elements, spaces)
  - Measurement (energy, temperature, etc.)
  - Unit (building/energy units)
- **Important Relationships:**
  - Dataset → MeasurementGroup (ns0__hasGroup)
  - MeasurementGroup → Measurement (ns0__hasMeasurement)
  - Measurement → Unit (ns0__hasUnit)
- **Structure:**
  - Focused on building structure and energy flows
  - Supports spatial and energy performance analysis

---

## ENGREEN (engreen.owl)
- **Domain:** ENGREEN, renewable energy and user data
- **Key Entities:**
  - Dataset (renewable datasets, user profiles)
  - MeasurementGroup (asset groupings)
  - Measurement (production, consumption, user data)
  - Unit (energy, power, etc.)
- **Important Relationships:**
  - Dataset → MeasurementGroup (ns0__hasGroup)
  - MeasurementGroup → Measurement (ns0__hasMeasurement, ns9__hasMeasurement)
  - Measurement → Unit (ns0__hasUnit, ns16__hasUnit)
- **Structure:**
  - Emphasizes renewable production and user-centric data
  - Modular, extensible for new asset types

---

## General Structure (all_pilots.owl)
- **Unified ontology** merges all pilots for cross-domain analysis
- **Consistent core entities and relationships**
- **Semantic and pilot-specific labels** for flexible querying
- **Supports both high-level and detailed exploration**
