#!/usr/bin/env python3
"""Discover where each pilot dataset/variable actually lives in the EnergyGuard data lake.

Connects READ-ONLY to the data lake (one PostgreSQL database per pilot) and writes three
editable files that scripts/ontology/build_all_pilots_owl.py reads (the build itself never connects):

  pilot_metadata/dataset_tables.csv          dataset  -> database, table, layout
  pilot_metadata/sensor_map.csv              variable -> lake sensor_id / pattern / column
  pilot_metadata/lake_unmapped_sensors.csv   lake sensors no metadata variable describes

Rows marked source=manual in dataset_tables.csv / match=manual in sensor_map.csv are kept as
they are on re-discovery, so hand corrections survive.

Credentials come from the environment (never hard-code them):
    DATALAKE_HOST (default REDACTED_HOST)  DATALAKE_PORT (default REDACTED_PORT)
    DATALAKE_USER (default REDACTED_USER)  DATALAKE_PASSWORD (required)

Usage:
    DATALAKE_PASSWORD=... python3 scripts/ontology/discover_data_lake.py
Requires: rdflib, psycopg2 (psycopg2-binary).

How the lake stores data
------------------------
Every pilot database has the same star schema in `public`:
    d_sensor(sensor_id, name, type_id, min_value, max_value, frequency)
    d_sensor_type(sensor_type_id, sensor_type)
    d_calendar(calendar_id, ..., datetime)
    f_tsdata(ts_id, calendar_id, sensor_id, f_value, corrected)   -- partitioned by month
i.e. time series are stored LONG: one row per reading, the variable is the sensor_id.
REA additionally has WIDE tables (one column per variable) in the `gis` and `cadastre` schemas.
"""
import csv
import difflib
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import psycopg2
import rdflib
from rdflib.namespace import RDFS

ROOT = Path(__file__).resolve().parents[2]
OWL_FILE = ROOT / "ontology" / "all_pilots.owl"
BASE_OWL = ROOT / "ontology" / "all_pilots_base.owl"
META = ROOT / "pilot_metadata"
TABLES_CSV = META / "dataset_tables.csv"
SENSOR_CSV = META / "sensor_map.csv"
UNMAPPED_CSV = META / "lake_unmapped_sensors.csv"

B = "https://www.energyguard.eu/ontology"
EG = rdflib.Namespace(B + "#")
MP = rdflib.Namespace(B + "/merged-pilots#")

DATABASES = {"RDN": "TEF1_RDN", "CIEMAT": "TEF2_CEDER", "BER": "TEF3_BER", "CEA": "TEF4_CEA",
             "CARTIF": "TEF5_CARTIF", "REA": "TEF6_REA", "ENGREEN": "TEF7_ENGREEN"}
LONG_TABLE = "public.f_tsdata"
TIMESTAMP_COLUMN = "public.d_calendar.datetime"
TIMESTAMP_NAMES = {"time", "timestamp", "collecttime"}

# Pilots whose variables are individual sensors stored in f_tsdata
SENSOR_PILOTS = {"CIEMAT", "BER", "CEA", "CARTIF"}

# ENGREEN: the lake keeps one sensor per device and signal (<device>_<signal>); the metadata
# describes signal types. Map the metadata's source column -> sensor_id LIKE pattern.
# ('_' is a LIKE wildcard, hence the escaping.)
ENGREEN_SIGNALS = {
    "Operational_monitoring_dataset": {
        "Active power(kW)": (r"%\_active\_power", "inverters and grid power sensors share this signal"),
        "Active power(W)": (r"%\_active\_power", "inverters and grid power sensors share this signal"),
        "Daily energy(kWh)": (r"%\_day\_cap", ""),
        "Total yield(kWh)": (r"%\_total\_cap", ""),
        "Positive active energy(kWh)": (r"%\_active\_cap", ""),
        "Negative active energy(kWh)": (r"%\_reverse\_active\_cap", ""),
        "Batteria SOC(%)": (r"%\_battery\_soc", ""),
        "Potenza di carica e scarica(kW)": (r"%\_ch\_discharge\_power", ""),
    },
    "Shelly_consumer_monitoring_dataset": {
        "Consumo": (r"%\_total\_act\_energy", "lake keeps the cumulative meter energy"),
        "Voltaggio minimo": (r"%\_voltage", "lake keeps instantaneous voltage, not the minimum"),
    },
}
ENGREEN_LAKE_DATASETS = set(ENGREEN_SIGNALS)

# REA monthly heat series lives in f_tsdata with one "sensor" per building
REA_LONG = {
    "Buildings_monthly_heat_series_ARCGIS_Server": {
        "Kadastra Nr.": "public.d_sensor.sensor_id",
        "Adrese": "public.d_sensor.name",
        "01.2021 - current_month._current_year": "public.f_tsdata.f_value",
    },
}
COLUMN_ALIASES = {"geometry": "geom"}

norm = lambda s: re.sub(r"[^a-z0-9]", "", str(s).lower())
like_to_regex = lambda p: re.compile("^" + re.escape(p).replace("%", ".*").replace(r"\\_", "_") + "$")


def connect(db):
    pw = os.environ.get("DATALAKE_PASSWORD")
    if not pw:
        sys.exit("DATALAKE_PASSWORD is not set")
    c = psycopg2.connect(host=os.environ.get("DATALAKE_HOST", "REDACTED_HOST"),
                         port=int(os.environ.get("DATALAKE_PORT", "REDACTED_PORT")),
                         user=os.environ.get("DATALAKE_USER", "REDACTED_USER"),
                         password=pw, dbname=db, connect_timeout=15)
    c.set_session(readonly=True, autocommit=True)
    cur = c.cursor()
    cur.execute("SET statement_timeout = '60s'")
    return c, cur


def load_ontology():
    g = rdflib.Graph()
    g.parse(OWL_FILE)
    datasets = []
    for pilot_cls, ds in g.subject_objects(MP.hasDataset):
        pilot = str(pilot_cls).split("#")[1]
        title = str(next(g.objects(ds, RDFS.label)))
        variables = []
        for v in g.objects(ds, EG.hasVariable):
            name = str(next(g.objects(v, RDFS.label)))
            # the column name in the pilot's file (sourceColumnName), else the label
            cols = [str(c) for c in g.objects(v, EG.sourceColumnName)]
            sid = [str(s) for s in g.objects(v, EG.sensorId)]
            variables.append({"iri": str(v).split("#")[1], "name": name,
                              "column": cols[0] if cols else name, "sensor_id": sid[0] if sid else ""})
        datasets.append({"pilot": pilot, "dataset": str(ds).split("#")[1], "title": title,
                         "variables": sorted(variables, key=lambda x: x["iri"])})
    return sorted(datasets, key=lambda d: (d["pilot"], d["dataset"]))


def read_csv(path, key):
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        return {tuple(r[k] for k in key): r for r in csv.DictReader(f)}


def write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    datasets = load_ontology()
    lake = {}            # pilot -> {sensor_id: (name, type, frequency)}
    rea_tables = {}      # schema.table -> [columns]
    for pilot, db in DATABASES.items():
        c, cur = connect(db)
        cur.execute("""SELECT s.sensor_id, s.name, t.sensor_type, s.frequency
                       FROM public.d_sensor s LEFT JOIN public.d_sensor_type t ON t.sensor_type_id = s.type_id""")
        lake[pilot] = {r[0]: r[1:] for r in cur.fetchall()}
        if pilot == "REA":
            cur.execute("""SELECT table_schema || '.' || table_name, column_name FROM information_schema.columns
                           WHERE table_schema IN ('gis', 'cadastre') ORDER BY table_schema, table_name, ordinal_position""")
            for t, col in cur.fetchall():
                rea_tables.setdefault(t, []).append(col)
        c.close()
        print(f"{pilot:8} {db:13} {len(lake[pilot]):5} sensors")

    old_tables = read_csv(TABLES_CSV, ("dataset",))
    old_sensors = read_csv(SENSOR_CSV, ("dataset", "variable"))
    table_rows, sensor_rows, used = [], [], defaultdict(set)
    device_dataset = {}  # ENGREEN device id -> dataset title

    for d in datasets:
        pilot, key = d["pilot"], d["dataset"]
        short = key[len("Dataset_"):]
        loc = {"pilot": pilot, "dataset": key, "title": d["title"], "database": "", "table": "",
               "layout": "", "source": "not_found"}
        var_rows = []
        generic_engreen = pilot == "ENGREEN" and short not in ENGREEN_LAKE_DATASETS
        if pilot in SENSOR_PILOTS or generic_engreen:
            by_norm = defaultdict(list)
            for sid in lake[pilot]:
                by_norm[norm(sid)].append(sid)
            for v in d["variables"]:
                row = {"pilot": pilot, "dataset": key, "variable": v["iri"], "name": v["name"],
                       "lake_sensor_id": "", "lake_sensor_pattern": "", "lake_column": "", "match": "none", "note": ""}
                cands = [v["column"], v["name"], v["sensor_id"]]
                # the lake adds a station/channel suffix: ENGREEN weather 'temp_c' -> 'temp_c_1'
                suffixed = sorted({s for c in cands if c for s in lake[pilot]
                                   if re.fullmatch(r"_\d+", s[len(c):] if s.lower().startswith(c.lower()) else "x")})
                exact = next((c for c in cands if c and c in lake[pilot]), None)
                fuzzy = next((by_norm[norm(c)][0] for c in cands if c and len(by_norm.get(norm(c), [])) == 1), None)
                # BER hour counters: metadata 'HC-PMP-C501' is 'PMP_C501_HC' in the lake
                counter = (v["column"].startswith("HC-")
                           and by_norm.get(norm(v["column"][3:] + "_HC"), [None])[0])
                # one metadata signal split in two in the lake: 'AS-Z201' -> AS_Z201_1, AS_Z201_2
                split = [s for s in lake[pilot] if re.fullmatch(re.escape(norm(v["column"])) + r"\d", norm(s))
                         and norm(s)[:-1] == norm(v["column"]) and s[-2] == "_"]
                if exact:
                    row.update(lake_sensor_id=exact, match="exact")
                elif fuzzy:
                    row.update(lake_sensor_id=fuzzy, match="normalised")
                elif counter:
                    row.update(lake_sensor_id=counter, match="normalised", note="hour counter: suffix _HC in the lake")
                elif len(suffixed) == 1:
                    row.update(lake_sensor_id=suffixed[0], match="normalised", note="the lake adds a numeric suffix")
                elif len(split) >= 2:
                    pattern = re.sub(r"_\d$", "", sorted(split)[0]).replace("_", r"\_") + r"\_%"
                    row.update(lake_sensor_pattern=pattern, match="pattern",
                               note="split in the lake: " + ", ".join(sorted(split)))
                    used[pilot].update(split)
                elif norm(v["column"]) in TIMESTAMP_NAMES:
                    row.update(lake_column=TIMESTAMP_COLUMN, match="timestamp")
                if row["lake_sensor_id"]:
                    used[pilot].add(row["lake_sensor_id"])
                var_rows.append(row)
            if pilot in SENSOR_PILOTS or any(r["lake_sensor_id"] or r["lake_sensor_pattern"] for r in var_rows):
                loc.update(database=DATABASES[pilot], table=LONG_TABLE, layout="long", source="lake")
            else:
                var_rows = []
        elif pilot == "ENGREEN" and short in ENGREEN_LAKE_DATASETS:
            loc.update(database=DATABASES[pilot], table=LONG_TABLE, layout="long", source="lake")
            signals = ENGREEN_SIGNALS[short]
            for v in d["variables"]:
                row = {"pilot": pilot, "dataset": key, "variable": v["iri"], "name": v["name"],
                       "lake_sensor_id": "", "lake_sensor_pattern": "", "lake_column": "", "match": "none", "note": ""}
                if v["column"] in signals:
                    pattern, note = signals[v["column"]]
                    hits = [s for s in lake[pilot] if like_to_regex(pattern).match(s)]
                    if hits:
                        row.update(lake_sensor_pattern=pattern, match="pattern", note=f"{len(hits)} lake sensors" + (f"; {note}" if note else ""))
                        used[pilot].update(hits)
                        for h in hits:
                            device_dataset[h.split("_", 1)[0]] = d["title"]
                elif norm(v["column"]) in TIMESTAMP_NAMES:
                    row.update(lake_column=TIMESTAMP_COLUMN, match="timestamp")
                var_rows.append(row)
        elif pilot == "REA" and short in REA_LONG:
            loc.update(database=DATABASES[pilot], table=LONG_TABLE, layout="long", source="lake")
            for v in d["variables"]:
                col = REA_LONG[short].get(v["column"]) or REA_LONG[short].get(v["name"])
                var_rows.append({"pilot": pilot, "dataset": key, "variable": v["iri"], "name": v["name"],
                                 "lake_sensor_id": "", "lake_sensor_pattern": "", "lake_column": col or "",
                                 "match": "column" if col else "none", "note": "one lake sensor per building"})
        elif pilot == "REA":
            # wide GIS / cadastre tables: pick the table whose columns best match the variables
            wanted = {norm(COLUMN_ALIASES.get(v["column"].lower(), v["column"])): v for v in d["variables"]}
            scored = sorted(((len(wanted.keys() & {norm(c) for c in cols}), t) for t, cols in rea_tables.items()), reverse=True)
            best = scored[0][0] if scored else 0
            if best >= 2 and best >= 0.5 * len(wanted):
                tables = sorted(t for s, t in scored if s == best)
                prefix = os.path.commonprefix(tables)
                if len(tables) == 1 or len(prefix) > len("gis.") + 3:   # e.g. gis.noise_2021_{diena,nakts,...}
                    loc.update(database=DATABASES[pilot], table=";".join(tables), layout="wide", source="lake")
                    actual = {norm(c): c for c in rea_tables[tables[0]]}
                    for nk, v in wanted.items():
                        col = actual.get(nk)
                        var_rows.append({"pilot": pilot, "dataset": key, "variable": v["iri"], "name": v["name"],
                                         "lake_sensor_id": "", "lake_sensor_pattern": "", "lake_column": col or "",
                                         "match": "column" if col else "none", "note": ""})
        if not var_rows:
            var_rows = [{"pilot": pilot, "dataset": key, "variable": v["iri"], "name": v["name"], "lake_sensor_id": "",
                         "lake_sensor_pattern": "", "lake_column": "", "match": "none", "note": ""} for v in d["variables"]]
        # keep manual corrections
        if old_tables.get((key,), {}).get("source") == "manual":
            loc = {k: old_tables[(key,)].get(k, "") for k in loc}
        for r in var_rows:
            old = old_sensors.get((key, r["variable"]))
            if old and old.get("match") == "manual":
                r.update({k: old.get(k, "") for k in r})
        table_rows.append(loc)
        sensor_rows.extend(sorted(var_rows, key=lambda r: r["variable"]))

    # suggestions for what is still unmatched (never applied automatically)
    for r in sensor_rows:
        if r["match"] != "none" or r["pilot"] not in SENSOR_PILOTS | {"ENGREEN"}:
            continue
        if r["pilot"] == "ENGREEN" and not any(x["dataset"] == r["dataset"] and x["match"] != "none" for x in sensor_rows):
            continue
        free = sorted(set(lake[r["pilot"]]) - used[r["pilot"]])
        keys = {norm(s): s for s in free}
        close = difflib.get_close_matches(norm(r["name"]), list(keys), n=3, cutoff=0.6)
        if close:
            r["note"] = "not in the lake under this name; closest lake sensors: " + ", ".join(keys[c] for c in close)
        else:
            r["note"] = "not in the lake under this name"
    # exact matches that may be the wrong signal: the lake also has <id>_PV
    for r in sensor_rows:
        if r["match"] == "exact" and r["lake_sensor_id"] + "_PV" in lake.get(r["pilot"], {}) \
                and "PV" in r["name"].upper() + " " + (r.get("note") or ""):
            r["note"] = f"check: lake also has {r['lake_sensor_id']}_PV"
    # where else an unmapped lake sensor is known from (hints for the pilots, never applied)
    base = rdflib.Graph()
    base.parse(BASE_OWL)
    base_names = defaultdict(dict)
    for s in set(base.subjects()):
        m = re.match(re.escape(B) + r"/(rdn|ciemat|ber|cea|cartif|rea|engreen)[/#]", str(s))
        if m:
            keys = {str(s).split("#")[-1]} | {str(o) for o in base.objects(s, RDFS.label)}
            for k in keys:
                base_names[m.group(1).upper()][norm(k)] = str(s).split("#")[-1]
    meta_names = defaultdict(dict)
    for dd in datasets:
        for v in dd["variables"]:
            for k in (v["name"], v["column"]):
                meta_names[dd["pilot"]][norm(k)] = (v["name"], dd["title"])
    unmatched_names = defaultdict(dict)
    for r in sensor_rows:
        if r["match"] == "none":
            dtitle = next(dd["title"] for dd in datasets if dd["dataset"] == r["dataset"])
            unmatched_names[r["pilot"]][norm(r["name"])] = (r["name"], dtitle)
    unmapped = []
    for pilot, sensors in sorted(lake.items()):
        if pilot == "REA":
            continue   # REA lake sensors are buildings (cadastre numbers), not variables
        used_norm = {norm(u): u for u in used[pilot]}
        for sid in sorted(set(sensors) - used[pilot]):
            name, stype, freq = sensors[sid]
            n, hint = norm(sid), ""
            if n in used_norm:
                hint = f"same sensor id as mapped {used_norm[n]} except letter case (duplicate in the lake?)"
            elif n in base_names[pilot]:
                hint = (f"described in the original {pilot} ontology ({base_names[pilot][n]}) "
                        "but not in the pilot metadata")
            elif pilot == "ENGREEN" and sid.split("_", 1)[0] in device_dataset:
                hint = f"signal of a device of '{device_dataset[sid.split('_', 1)[0]]}' (signal not described in the metadata)"
            elif sid.endswith("_PV") and sid[:-3] in used[pilot]:
                hint = (f"check: the metadata's PV signal is mapped to {sid[:-3]}; "
                        f"{sid} may be the PV one and {sid[:-3]} the consumption one")
            else:
                stem = norm(re.sub(r"_\d+$", "", sid))
                pool = unmatched_names[pilot] or meta_names[pilot]
                # 1) one name contains the other (BATERIA_PEPA_I ~ 'BATERIA PB-ACIDO PEPA I' does not, but
                #    TURBINA_C ~ 'TURBINA [consumption]' does); 2) similar spelling, but never for instrument
                #    tags like PT222 vs PT220, which are different sensors
                contain = sorted(k for k in pool if len(stem) >= 4 and (stem in k or k in stem))
                is_tag = re.fullmatch(r"[A-Za-z]{1,5}[-_]?\d+[A-Za-z]?", sid) is not None
                close = contain or ([] if is_tag else difflib.get_close_matches(stem, list(pool), n=1, cutoff=0.75))
                if close:
                    vname, dtitle = pool[close[0]]
                    hint = f"possibly '{vname}' of '{dtitle}' (similar name, not yet matched)" if pool is unmatched_names[pilot] \
                        else f"possibly '{vname}' of '{dtitle}' (similar name)"
            unmapped.append({"pilot": pilot, "database": DATABASES[pilot], "sensor_id": sid, "name": name,
                             "sensor_type": stype, "frequency_s": freq, "hint": hint})

    # the lake's own sensor type for every located variable (used only where the metadata says nothing)
    for r in sensor_rows:
        sensors = lake.get(r["pilot"], {})
        if r["lake_sensor_id"] in sensors:
            r["lake_sensor_type"] = sensors[r["lake_sensor_id"]][1] or ""
        elif r["lake_sensor_pattern"]:
            rx = like_to_regex(r["lake_sensor_pattern"])
            r["lake_sensor_type"] = "/".join(sorted({t or "" for s, (_, t, _) in sensors.items() if rx.match(s)}))
        else:
            r["lake_sensor_type"] = ""
    write_csv(TABLES_CSV, ["pilot", "dataset", "title", "database", "table", "layout", "source"], table_rows)
    write_csv(SENSOR_CSV, ["pilot", "dataset", "variable", "name", "lake_sensor_id", "lake_sensor_pattern",
                           "lake_column", "lake_sensor_type", "match", "note"], sensor_rows)
    write_csv(UNMAPPED_CSV, ["pilot", "database", "sensor_id", "name", "sensor_type", "frequency_s", "hint"], unmapped)

    from collections import Counter
    print("\ndatasets:", dict(Counter(r["source"] for r in table_rows)))
    for pilot in DATABASES:
        c = Counter(r["match"] for r in sensor_rows if r["pilot"] == pilot)
        print(f"  {pilot:8} variables {sum(c.values()):4}  " + "  ".join(f"{k}={v}" for k, v in sorted(c.items())))
    print("lake sensors not described by any metadata variable:", dict(Counter(r["pilot"] for r in unmapped)))
    kinds = Counter((r["pilot"], r["hint"].split(" (")[0].split(" '")[0][:40] if r["hint"] else "no hint") for r in unmapped)
    for (p, k), c in sorted(kinds.items()):
        print(f"    {p:8} {c:4}  {k}")
    print(f"wrote {TABLES_CSV.name}, {SENSOR_CSV.name}, {UNMAPPED_CSV.name}")


if __name__ == "__main__":
    main()
