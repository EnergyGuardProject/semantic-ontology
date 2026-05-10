# EnergyGuard Pilots – Ontology High-Level Overview

---

## Pilot 1 (pilot1_f.owl, pilot1_ts.owl)
- **Domain:** Faults and Timeseries for Pilot 1
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

## Pilot 2 (pilot2.owl)
- **Domain:** Pilot 2 energy and system ontology
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

## Pilot 3 (pilot3_cea.owl, pilot3_cartif.owl, pilot3_ber.owl)
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
  - Labels: Pilot3CEA, Pilot3CARTIF, Pilot3BER

---

## Pilot 4 (not explicitly listed, but present in all_pilots.owl)
- **Domain:** Riga pilot, building and energy ontology
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

## Pilot 5 (pilot5_engreen.owl)
- **Domain:** EnGreen pilot, renewable energy and user data
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
