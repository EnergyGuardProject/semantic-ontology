#!/usr/bin/env python3
"""Build the single EnergyGuard ontology file that is imported into Neo4j.

    ontology/all_pilots_base.owl   (merged pilot ontologies: classes, properties, sample individuals)
  + pilot_metadata/*.xlsx          (dataset + variable metadata delivered by the pilots; not in git)
  + ontology/mappings/*.csv        (where each dataset/variable lives in the data lake)
  = ontology/all_pilots.owl        (the ONE file loaded by n10s; generated, do not edit)

Usage:
    python3 utils/ontology/build_all_pilots_owl.py            # writes ontology/all_pilots.owl
    python3 utils/ontology/build_all_pilots_owl.py --check    # build + print stats, don't write

Requires: rdflib, openpyxl.

What it does
------------
1. Loads the base ontology and applies the clean-up pass (idempotent):
   - object references left in the old core namespace (…/ontology#X) are moved to
     the namespace of the pilot that uses them;
   - hasPilot / hasSubPilot / has*Entity use the merged-pilots# namespace;
   - cp1253 mojibake is repaired; author-local file:/// IRIs are replaced;
   - prefixed names used as IRIs (xsd:float, unit:DegreeCelsius, …) are expanded.
2. Declares every core eg: property used in the graph (they were used but never defined).
3. Adds the pilot metadata:
   - every dataset    -> a dcat:Dataset individual in the pilot's namespace, linked from
                         its pilot class with mp:hasDataset, with eg: metadata properties;
   - every variable   -> an eg:Variable individual linked with eg:hasVariable. Sensor tags of
                         time-series pilots are matched to the existing measurement individual
                         (by local name, label or eg:storedInDatabaseColumn), so the metadata
                         lands on the node that the ontology already uses.
4. The pilot metadata is the source of truth. For a matched node, the base ontology's
   rdfs:label, eg:storedInDatabaseColumn/Table and (when the metadata gives a unit)
   eg:unit / eg:unitUCUM / eg:hasUnit are replaced by the metadata values.
5. Every dataset references one PostgreSQL table (eg:storedInDatabaseTable "schema.table"),
   read from ontology/mappings/dataset_tables.csv. Datasets missing from that CSV get a default
   name (<pilot>.<dataset_title_snake_case>) and are appended to it, so edit the CSV to point
   at the real tables and rebuild. Each variable carries its column (eg:storedInDatabaseColumn)
   and its dataset's table, which is what the 02/05 mapping queries read.
6. For the pilots whose sensors are delivered in the metadata (CIEMAT, BER, CEA, CARTIF), base
   content the metadata does not back is removed: sensor individuals of the old sample
   datasets, those sample datasets, measurement groups left empty, and references to pilot
   nodes that exist nowhere. RDN (no metadata yet), REA and ENGREEN are left untouched.
7. Every time-series variable without a measurement class gets one (eg:TemperatureMeasurement,
   eg:PowerMeasurement, ...), decided from the metadata (unit, sensor type, kind) and only when
   that says nothing from the data lake's sensor type. Decisions and metadata/lake disagreements
   are written to output/reports/variable_classes_report.csv.
"""
import argparse
import csv
import hashlib
import logging
import os
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote

import openpyxl
from standards_layer import add_standards_layer
import rdflib
from rdflib import BNode, Literal, Namespace, URIRef
from rdflib.namespace import DCAT, DCTERMS, OWL, RDF, RDFS, XSD

ROOT = Path(__file__).resolve().parents[2]
BASE_OWL = ROOT / "ontology" / "all_pilots_base.owl"
META_DIR = ROOT / "pilot_metadata"          # partner workbooks (not in git)
MAPPINGS_DIR = ROOT / "ontology" / "mappings"  # lake mappings (in git)
REPORTS_DIR = ROOT / "output" / "reports"
OUT_OWL = ROOT / "ontology" / "all_pilots.owl"

BASE = "https://www.energyguard.eu/ontology"
EG = Namespace(BASE + "#")
MP = Namespace(BASE + "/merged-pilots#")
DATA = "https://www.energyguard.eu/data/"

# one namespace per pilot organisation
RDN = Namespace(BASE + "/rdn#")            # RDN datasets (its vocabularies: /rdn/faults#, /rdn/timeseries#)
CIEMAT = Namespace(BASE + "/ciemat#")
BER = Namespace(BASE + "/ber#")
CEA = Namespace(BASE + "/cea#")
CARTIF = Namespace(BASE + "/cartif#")
REA = Namespace(BASE + "/rea#")
ENGREEN = Namespace(BASE + "/engreen#")

# prefixes for the EnergyGuard namespaces (also registered in n10s by the import script)
EG_PREFIXES = {
    "eg": str(EG), "mp": str(MP),
    "rdn": str(RDN), "rdnf": BASE + "/rdn/faults#", "rdnts": BASE + "/rdn/timeseries#",
    "ciemat": str(CIEMAT), "ber": str(BER), "cea": str(CEA), "cartif": str(CARTIF),
    "rea": str(REA), "engreen": str(ENGREEN),
}

# --------------------------------------------------------------------------------------
# 1. Clean-up pass for the base ontology
# --------------------------------------------------------------------------------------
# any pilot namespace: https://www.energyguard.eu/ontology/<organisation>[/<part>]#
PILOT_RE = re.compile(r"^(https://www\.energyguard\.eu/ontology/(?!merged-pilots)[^#]+#)")
STRUCT_PREDICATES = {"hasPilot", "hasSubPilot", "hasClassEntity", "hasPropertyEntity", "hasIndividualEntity"}
CURIE_NS = {
    "xsd": str(XSD), "owl": str(OWL), "rdfs": str(RDFS),
    "unit": "http://qudt.org/vocab/unit/", "qudt": "http://qudt.org/schema/qudt/",
    "sosa": "http://www.w3.org/ns/sosa/", "ssn": "http://www.w3.org/ns/ssn/",
    "dcat": str(DCAT), "saref": "https://saref.etsi.org/core/",
    "s4ener": "https://saref.etsi.org/saref4ener/", "foaf": "http://xmlns.com/foaf/0.1/",
    "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#", "bot": "https://w3id.org/bot#",
    "engreen": str(ENGREEN),
}
CURIE_RE = re.compile(r"^([A-Za-z][A-Za-z0-9]*):([^/].*)$")


def pilot_ns(term):
    m = PILOT_RE.match(str(term))
    return m.group(1) if m else None


def fix_mojibake(text):
    for _ in range(3):
        if not re.search("[ΒΓΞÂÃ]", text):
            break
        try:
            fixed = text.encode("cp1253").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
        if fixed == text:
            break
        text = fixed
    return text


# unit names the original pilot ontologies invented -> the real QUDT unit codes
LEGACY_QUDT = {
    "KiloWatt": "KiloW", "Watt": "W", "Percent": "PERCENT", "DegreeCelsius": "DEG_C", "Pascal": "PA",
    "CubicMeterPerHour": "M3-PER-HR", "KiloWattHour": "KiloW-HR", "Volt": "V", "Ampere": "A", "Liter": "L",
    "WattPerSquareMeter": "W-PER-M2", "SiemensPerMeter": "S-PER-M", "Kilogram": "KiloGM",
    "KilowattHour-PER-M2": "KiloW-HR-PER-M2", "KiloGram-PER-M2": "KiloGM-PER-M2", "TonneMetric": "TONNE",
}


def fix_iri(term, subject_ns, stats):
    s = str(term)
    if s.startswith("http://qudt.org/vocab/unit/") and s.rsplit("/", 1)[-1] in LEGACY_QUDT:
        stats["qudt_units_fixed"] += 1
        return URIRef("http://qudt.org/vocab/unit/" + LEGACY_QUDT[s.rsplit("/", 1)[-1]])
    if s.startswith("file:///"):
        stats["file_iri"] += 1
        if s.endswith("_f.owl#Measurement"):
            return URIRef(BASE + "/rdn/faults#Measurement")
        return URIRef(DATA + unquote(s).rsplit("/", 1)[-1].replace(" ", "_"))
    if s.startswith(str(EG)) and subject_ns:
        stats["eg_ref"] += 1
        return URIRef(subject_ns + s[len(str(EG)):])
    m = CURIE_RE.match(s)
    if m and not s.startswith(("http:", "https:", "urn:", "file:", "mailto:")):
        prefix, local = m.groups()
        if prefix == "eg" and subject_ns:
            stats["curie"] += 1
            return URIRef(subject_ns + local)
        if prefix in CURIE_NS:
            stats["curie"] += 1
            return URIRef(CURIE_NS[prefix] + local)
    return term


def stable_bnodes(g):
    """Replace random blank-node ids by ids derived from the node's content (stable output)."""
    ids = {}
    for b in {t for t in g.subjects() if isinstance(t, BNode)}:
        content = sorted(f"{p} {o}" for p, o in g.predicate_objects(b) if not isinstance(o, BNode))
        parents = sorted(f"{s} {p}" for s, p in g.subject_predicates(b))
        ids[b] = BNode("b" + hashlib.sha1("\n".join(parents + content).encode()).hexdigest()[:16])
    out = rdflib.Graph()
    for prefix, ns in g.namespaces():
        out.bind(prefix, ns, override=True)
    for s, p, o in g:
        out.add((ids.get(s, s), p, ids.get(o, o)))
    return out


def clean_base(g, stats):
    g = stable_bnodes(g)
    out = rdflib.Graph()
    for prefix, ns in g.namespaces():
        out.bind(prefix, ns, override=True)
    for s, p, o in g:
        sns = pilot_ns(s)
        s2 = fix_iri(s, sns, stats) if isinstance(s, URIRef) and not str(s).startswith(str(EG)) else s
        if str(p).startswith(str(EG)) and str(p)[len(str(EG)):] in STRUCT_PREDICATES:
            p2 = MP[str(p)[len(str(EG)):]]
            stats["struct_pred"] += 1
        else:
            p2 = fix_iri(p, None, stats)
        if isinstance(o, URIRef):
            o2 = fix_iri(o, sns, stats)
        elif isinstance(o, Literal):
            if o.datatype and o.ill_typed:  # e.g. xsd:date "end" in the EnGreen source
                stats["ill_typed_dropped"] += 1
                continue
            txt = fix_mojibake(str(o))
            if txt != str(o):
                stats["mojibake"] += 1
            o2 = Literal(txt, lang=o.language, datatype=fix_iri(o.datatype, None, stats) if o.datatype else None)
        else:
            o2 = o
        out.add((s2, p2, o2))
    return out


# --------------------------------------------------------------------------------------
# 2. Vocabulary for the metadata
# --------------------------------------------------------------------------------------
DATASET_FIELDS = {  # normalised Excel field name -> property
    "title": DCTERMS.title,
    "description": DCTERMS.description,
    "location": EG.location,
    "system described": EG.systemDescribed,
    "source system": EG.sourceSystem,
    "temporal coverage": EG.temporalCoverage,
    "time resolution": EG.timeResolution,
    "time zone": EG.timeZone,
    "update frequency": EG.updateFrequency,
    "file format": EG.fileFormat,
    "missing values": EG.missingValues,
    "licence": EG.licence,
    "data owner / contact": EG.dataOwnerContact,
    "data owner/contact": EG.dataOwnerContact,
}
VARIABLE_FIELDS = {  # normalised Excel column header -> property ('name' handled separately)
    "description": DCTERMS.description,
    "spanish description": DCTERMS.description,  # added with @es
    "unit": EG.unit,
    "sensor id": EG.sensorId,
    "sensor type": EG.sensorType,
    "data type": EG.dataType,
    "variable kind": EG.variableKind,
    "valid range": EG.validRange,
    "min": EG.minValue,
    "max": EG.maxValue,
    "decimals": EG.decimals,
    "threshold": EG.recordThreshold,
    "aggregation": EG.aggregation,
    "sampling": EG.sampling,
    "sampling time": EG.sampling,
    "sign convention": EG.signConvention,
    "code list": EG.codeList,
    "asset / subsystem": EG.subsystem,
    "subsystem": EG.subsystem,
    "name (source file)": EG.sourceColumnName,
    "feature name (latvian)": EG.sourceColumnName,
}
EXTRA_DATASET_PROPS = {
    EG.datasetType: "Dataset type (time series, geospatial, tabular, …) as listed in the delivery overview.",
    EG.sourceUrl: "Landing page / open-data URL of the dataset.",
    EG.recordCount: "Size of the dataset as reported by the pilot (free text).",
    EG.notes: "Additional notes reported by the pilot.",
}
VOCAB_COMMENTS = {
    EG.location: "Site name, city, country.",
    EG.systemDescribed: "Physical system or process the dataset covers.",
    EG.sourceSystem: "System the data comes from (SCADA, PLC, smart meter, open data portal, …).",
    EG.temporalCoverage: "Start and end of the full dataset available.",
    EG.timeResolution: "Interval between values.",
    EG.timeZone: "Time zone of the timestamps and DST handling.",
    EG.updateFrequency: "One-off, periodically updated or streamed.",
    EG.fileFormat: "Format, delimiter, decimal separator.",
    EG.missingValues: "Marker used for missing data and its meaning.",
    EG.licence: "Terms of use.",
    EG.dataOwnerContact: "Organisation that owns the data (personal names and emails are not published).",
    EG.unit: "Unit of measurement as text (as delivered by the pilot).",
    EG.sensorId: "Tag or asset identifier.",
    EG.sensorType: "Kind of sensor or equipment.",
    EG.dataType: "float | integer | boolean | text | date | timestamp | geometry: the PostgreSQL / data-lake words (float = double precision); other text kept as delivered.",
    EG.variableKind: "measured | calculated | setpoint | state | alarm | output | static | modelled | … (lower case).",
    EG.validRange: "Expected range of values (free text).",
    EG.minValue: "Expected minimum value.",
    EG.maxValue: "Expected maximum value.",
    EG.decimals: "Number of decimals recorded.",
    EG.recordThreshold: "Difference between consecutive values that triggers a new record.",
    EG.aggregation: "instantaneous | mean | sum | cumulative | none.",
    EG.aggregationNote: "The pilot's original aggregation text when it carries detail beyond eg:aggregation (e.g. the period).",
    EG.valueFormat: "How values are written when the pilot put it in the unit column (e.g. DD.MM.YYYY, EPSG:3059, one of A / B / C).",
    EG.sampling: "Sampling strategy / sampling time.",
    EG.signConvention: "Meaning of positive and negative values.",
    EG.codeList: "Meaning of coded values (states, alarms).",
    EG.subsystem: "Equipment / asset / subsystem the variable belongs to.",
    EG.databaseServer: "Data lake holding the dataset (the host address is not published).",
    EG.databaseSystem: "Database system of the data lake.",
    EG.storedInDatabase: "Data lake database holding the dataset (one per pilot, e.g. TEF3_BER).",
    EG.storedInDatabaseTable: "Table holding the dataset (schema.table). A variable's table is the table of its dataset.",
    EG.tableLayout: "long = one row per reading (public.f_tsdata: sensor_id, calendar_id -> d_calendar.datetime, f_value); wide = one column per variable.",
    EG.storedInDatabaseColumn: "Column holding the variable: a column of a wide table, or a lake column such as public.d_calendar.datetime.",
    EG.dataLakeSensorId: "sensor_id of the variable in the data lake (rows of public.f_tsdata / public.d_sensor).",
    EG.dataLakeSensorPattern: "SQL LIKE pattern for the variable's sensor_ids when the lake keeps one sensor per device (e.g. %\\_day\\_cap).",
    EG.dataLakeMatch: "How the variable was located in the lake: exact | normalised | pattern | column | timestamp | none.",
    EG.sourceColumnName: "Column name in the file the pilot delivered, when it differs from the label.",
    **EXTRA_DATASET_PROPS,
}
EMPTY = {"", "-", "–", "—", "n/a", "na", "none", "not applicable", "tbd", "all", "time series"}


def clean(v):
    if v is None:
        return None
    s = re.sub(r"\s+", " ", str(v).replace("\t", " ")).strip()
    return None if s.lower() in EMPTY else s


def norm(v):
    return (clean(v) or "").lower()


def slug(text, maxlen=80):
    t = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    t = re.sub(r"[^A-Za-z0-9]+", "_", t).strip("_")
    return (t[:maxlen].rstrip("_")) or "x"


def declare_vocab(g):
    g.add((EG.Variable, RDF.type, OWL.Class))
    g.add((EG.Variable, RDFS.label, Literal("Variable", lang="en")))
    g.add((EG.Variable, RDFS.comment, Literal("A column of a pilot dataset (a sensor signal, calculated value, setpoint, state or attribute), described by the pilot metadata.", lang="en")))
    g.add((DCAT.Dataset, RDF.type, OWL.Class))
    g.add((DCAT.Dataset, RDFS.label, Literal("Dataset", lang="en")))
    for prop, dom, rng, label in [
        (MP.hasDataset, MP.Pilot, DCAT.Dataset, "has dataset"),
        (EG.hasVariable, DCAT.Dataset, EG.Variable, "has variable"),
    ]:
        g.add((prop, RDF.type, OWL.ObjectProperty))
        g.add((prop, RDFS.domain, dom))
        g.add((prop, RDFS.range, rng))
        g.add((prop, RDFS.label, Literal(label, lang="en")))
    for prop, comment in VOCAB_COMMENTS.items():
        g.add((prop, RDF.type, OWL.DatatypeProperty))
        g.add((prop, RDFS.comment, Literal(comment, lang="en")))
        g.add((prop, RDFS.label, Literal(re.sub(r"(?<!^)([A-Z])", r" \1", prop.split("#")[-1]).lower(), lang="en")))
    # declare every other core eg: property already used by the pilot ontologies
    declared = set(g.subjects(RDF.type, OWL.ObjectProperty)) | set(g.subjects(RDF.type, OWL.DatatypeProperty))
    for p in set(g.predicates()):
        if str(p).startswith(str(EG)) and p not in declared:
            is_obj = any(isinstance(o, URIRef) for o in g.objects(None, p))
            g.add((p, RDF.type, OWL.ObjectProperty if is_obj else OWL.DatatypeProperty))
            g.add((p, RDFS.label, Literal(re.sub(r"(?<!^)([A-Z])", r" \1", p.split("#")[-1]).lower(), lang="en")))


# --------------------------------------------------------------------------------------
# 3. Excel readers  (each returns a list of {"fields": {...}, "variables": [{...}], "scope": ...})
# --------------------------------------------------------------------------------------
def rows(ws):
    return [list(r) for r in ws.iter_rows(values_only=True)]


def blank(r):
    return all(clean(c) is None and (c is None or str(c).strip() == "") for c in r)


def read_kv_fields(rs, stop_marker="variable metadata"):
    """Dataset fields from 'Field | Value' or 'Field | Description | Value | Applies to' layouts."""
    fields, value_col = {}, 1
    for r in rs:
        key = norm(r[0] if r else None)
        if key.startswith(stop_marker):
            break
        if key == "field":
            hdr = [norm(c) for c in r]
            value_col = 2 if len(hdr) > 2 and hdr[1] == "description" else 1
            continue
        if key in DATASET_FIELDS and len(r) > value_col:
            v = clean(r[value_col])
            if v:
                fields[key] = v
    return fields


def read_var_table(rs, header_idx):
    hdr = [norm(c) for c in rs[header_idx]]
    out = []
    for r in rs[header_idx + 1:]:
        if blank(r):
            if out:
                break
            continue
        rec = {hdr[i]: clean(c) for i, c in enumerate(r) if i < len(hdr) and hdr[i]}
        name = rec.get("name") or rec.get("name (d6.2)") or rec.get("tag") or rec.get("feature name (english)")
        if not name:
            continue
        rec["name"] = name
        out.append(rec)
    return out


def find_row(rs, pred, start=0):
    for i in range(start, len(rs)):
        if rs[i] and pred([norm(c) for c in rs[i]]):
            return i
    return None


def read_ciemat(path):
    rs = rows(openpyxl.load_workbook(path, read_only=True, data_only=True).active)
    fields = read_kv_fields(rs)
    hdr_i = find_row(rs, lambda r: r[0] == "field" and any(c.startswith("meter") for c in r))
    variables = []
    if hdr_i is not None:
        cols = [i for i, c in enumerate(rs[hdr_i]) if norm(c).startswith("meter")]
        recs = {c: {} for c in cols}
        for r in rs[hdr_i + 1:]:
            key = norm(r[0])
            if not key:
                continue
            for c in cols:
                v = clean(r[c]) if c < len(r) else None
                if v:
                    recs[c][key] = v
        variables = [rec for rec in recs.values() if rec.get("name")]
    return [{"fields": fields, "variables": variables, "scope": "pilot"}]


def read_ber(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    dbs = rows(wb["Databases"])
    hdr = [norm(c) for c in dbs[0]]
    signals = rows(wb["Signals"])
    variables = read_var_table(signals, 0)
    steps = defaultdict(list)
    for r in rows(wb["Step Legend"])[1:]:
        if r and clean(r[0]) and r[1] is not None:
            steps[clean(r[0])].append(f"{r[1]} = {clean(r[2]) or ''}".strip())
    for v in variables:
        if v["name"] in steps:
            legend = "; ".join(steps[v["name"]])
            v["code list"] = f"{v['code list']}; {legend}" if v.get("code list") else legend
    out = []
    for r in dbs[1:]:
        if blank(r):
            continue
        fields = {hdr[i]: clean(c) for i, c in enumerate(r) if i < len(hdr) and hdr[i] in DATASET_FIELDS and clean(c)}
        out.append({"fields": fields, "variables": variables, "scope": "pilot"})
    return out


def read_simple(path, ds_sheet, var_sheet):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    fields = read_kv_fields(rows(wb[ds_sheet]))
    vs = rows(wb[var_sheet])
    return [{"fields": fields, "variables": read_var_table(vs, 0), "scope": "pilot"}]


def read_engreen(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = []
    for ws in wb:
        rs = rows(ws)
        fields = read_kv_fields(rs)
        if not fields:
            continue
        hi = find_row(rs, lambda r: r[0].startswith("name"), find_row(rs, lambda r: r[0].startswith("variable metadata")) or 0)
        out.append({"fields": fields, "variables": read_var_table(rs, hi) if hi is not None else [], "scope": "dataset"})
    return out


def read_rea(path):
    """REA sheet: blocks separated by blank rows. Title row, info rows (URL, size, notes),
    'Feature name (latvian) | Feature name (english) | Unit | Description' header, variable rows.
    Lines like 'A) Existing buildings' / 'BIS Format for …' start a sub-dataset of the current block."""
    rs = rows(openpyxl.load_workbook(path, read_only=True, data_only=True)["Metadata"])
    datasets, main_title, cur, in_vars = [], None, None, False
    roles = {}
    HEADER_ROLES = {"feature name (latvian)": "lv", "feature name (english)": "en", "feature": "en",
                    "unit": "unit", "description": "desc", "format/type": "dtype"}

    def is_header(r):
        return norm(r[0]).startswith("feature name") or norm(r[0]) == "feature"

    def new(title):
        d = {"fields": {"title": title}, "variables": [], "scope": "dataset", "info": []}
        datasets.append(d)
        return d

    prev_blank = True
    for r in rs:
        r = (r + [None] * 6)[:6]
        if blank(r):
            prev_blank, in_vars = True, False
            continue
        c0 = clean(r[0])
        if is_header(r):
            in_vars = True
            roles = {i: HEADER_ROLES[norm(c)] for i, c in enumerate(r) if norm(c) in HEADER_ROLES}
            if cur is None:
                cur = new(main_title or "Riga dataset")
            prev_blank = False
            continue
        sub = c0 and (re.match(r"^[A-Z]\) ", c0) or c0.lower().startswith("bis format"))
        if in_vars and not sub:
            val = {role: clean(r[i]) for i, role in roles.items()}
            lv, en = val.get("lv"), val.get("en")
            name = en or lv
            if name and name != "....":
                rec = {"name": name, "unit": val.get("unit"), "description": val.get("desc"),
                       "data type": val.get("dtype")}
                # 3D-geometry rows give a format ("x, y, z", "nx, ny, nz", face indices) in the
                # Format/Type column: that is geometry; keep the format text in the description
                dtype = val.get("dtype")
                if dtype and _base(dtype) not in DATA_TYPES and "," in dtype or (dtype and "//" in dtype):
                    rec["data type"] = "geometry"
                    rec["description"] = f"{val.get('desc') or name} (format: {dtype})"
                if lv and lv != name:
                    rec["feature name (latvian)"] = lv
                extra = " ".join(x for i, x in enumerate(clean(c) for c in r) if x and i not in roles)
                if extra:
                    rec["code list"] = extra
                cur["variables"].append(rec)
            prev_blank = False
            continue
        if sub:
            in_vars = False
            cur = new(f"{main_title} – {c0}" if main_title else c0)
            if clean(r[1]):
                cur["fields"]["recordCount"] = clean(r[1])
            # the main block had no variables of its own: drop its empty placeholder
            if len(datasets) >= 2 and datasets[-2]["fields"]["title"] == main_title and not datasets[-2]["variables"]:
                parent = datasets.pop(-2)
                cur["info"] = parent["info"] + cur["info"]
        elif prev_blank:
            main_title = c0
            cur = new(c0)
        else:  # info row of the current block
            for x in (clean(c) for c in r):
                if not x:
                    continue
                if x.startswith("http"):
                    cur["fields"].setdefault("sourceUrl", x)
                elif re.match(r"^[\d\s,]+(data rows|samples?)", x) or re.search(r"\d+ samples?", x):
                    cur["fields"].setdefault("recordCount", x)
                else:
                    cur["info"].append(x)
        prev_blank = False
    for d in datasets:
        if d["info"]:
            d["fields"]["notes"] = " | ".join(d.pop("info"))
        else:
            d.pop("info")
    return [d for d in datasets if d["variables"] or len(d["fields"]) > 1]


def read_delivered(path):
    rs = rows(openpyxl.load_workbook(path, read_only=True, data_only=True)["Delivered"])
    hdr = [norm(c) for c in rs[0]]
    return [{hdr[i]: clean(c) for i, c in enumerate(r) if i < len(hdr)} for r in rs[1:] if not blank(r)]


# --------------------------------------------------------------------------------------
# 4. Writing metadata into the graph
# --------------------------------------------------------------------------------------
class MetadataWriter:
    def __init__(self, g, stats):
        self.g, self.stats = g, stats
        self.index = {}
        self.claimed = set()
        self.tables = {}          # dataset IRI -> row of ontology/mappings/dataset_tables.csv
        self.current_dataset = None
        self.sensor_map = {}      # (dataset, variable) -> row of ontology/mappings/sensor_map.csv
        self.located = set()
        self.unmapped_units = set()
        self.overridden = set()   # base nodes whose base name/unit/table were replaced by the metadata

    def _index(self, ns):
        if ns in self.index:
            return self.index[ns]
        idx, kinds = {}, {}
        for s in set(self.g.subjects()):
            if not str(s).startswith(str(ns)):
                continue
            types = set(self.g.objects(s, RDF.type))
            schema = bool(types & {OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty, OWL.Ontology})
            kinds[str(s)[len(str(ns)):]] = schema
            if schema:
                continue
            keys = {str(s)[len(str(ns)):]}
            keys |= {str(o).strip() for o in self.g.objects(s, RDFS.label)}
            keys |= {str(o).strip() for o in self.g.objects(s, EG.storedInDatabaseColumn)}
            for k in keys:
                idx.setdefault(k, s)
        self.index[ns] = (idx, kinds)
        return self.index[ns]

    def dataset(self, ns, pilot_cls, fields, delivered, schema, configured=None):
        title = fields.get("title") or "Dataset"
        ds = ns["Dataset_" + slug(title)]
        g = self.g
        local = str(ds).split("#")[-1]
        self.current_dataset = local
        row = (configured or {}).get(local) or {}
        self.tables[str(ds)] = row
        if row.get("database"):  # where the data really lives (utils/ontology/discover_data_lake.py)
            g.add((ds, EG.databaseServer, Literal(DATA_LAKE_SERVER)))
            g.add((ds, EG.databaseSystem, Literal("PostgreSQL")))
            g.add((ds, EG.storedInDatabase, Literal(row["database"])))
            for table in filter(None, row.get("table", "").split(";")):
                g.add((ds, EG.storedInDatabaseTable, Literal(table)))
            if row.get("layout"):
                g.add((ds, EG.tableLayout, Literal(row["layout"])))
            self.stats["datasets_located"] += 1
        g.add((ds, RDF.type, DCAT.Dataset))
        g.add((ds, RDF.type, OWL.NamedIndividual))
        g.add((ds, RDFS.label, Literal(title, lang="en")))
        g.add((pilot_cls, MP.hasDataset, ds))
        for key, val in fields.items():
            prop = DATASET_FIELDS.get(key) or EG[key]
            if prop == EG.dataOwnerContact:  # no personal names or emails in the public ontology
                val = str(g.value(pilot_cls, RDFS.label) or val)
            g.add((ds, prop, Literal(val, lang="en") if prop in (DCTERMS.title, DCTERMS.description) else Literal(val)))
        d = delivered.get(norm(title)[:40])
        if d:
            if d.get("dataset type"):
                g.add((ds, EG.datasetType, Literal(d["dataset type"])))
            if d.get("short description") and "description" not in fields:
                g.add((ds, DCTERMS.description, Literal(d["short description"], lang="en")))
        self.stats["datasets"] += 1
        return ds

    def variable(self, ns, ds, rec, scope, sibling_names=()):
        g = self.g
        name = rec["name"]
        source = rec.get("name (source file)")
        node = None
        if scope == "pilot":  # sensor tags: reuse the measurement individual if it exists
            idx, kinds = self._index(ns)
            node = idx.get(name)
            if node is None:
                # fuzzy matches must not steal the node another column of this dataset names exactly
                for key in (slug(name), rec.get("sensor id")):
                    if key and key not in sibling_names and key in idx:
                        node = idx[key]
                        break
            if node is not None:
                self.stats["vars_matched"] += 1
            else:
                local = slug(name)
                if kinds.get(local) or local in sibling_names or ns[local] in self.claimed:
                    local += "_var"
                node = ns[local]
                idx[name] = node
            self.claimed.add(node)
        else:  # dataset-scoped columns (same column name means different things in different datasets)
            col = source or rec.get("feature name (latvian)") or name
            node = ns[f"{ds.split('#')[-1][len('Dataset_'):]}__{slug(col, 120)}"]
        if (node, RDF.type, EG.Variable) not in g:
            self.stats["vars_new" if (node, None, None) not in g else "vars_enriched"] += 1
        file_column = source or rec.get("feature name (latvian)") or name
        value_format = None
        if rec.get("unit"):
            rec["unit"] = UNIT_SPELLING.get(rec["unit"].strip(), rec["unit"].strip())
            if rec["unit"] in NOT_UNITS:
                dtype, value_format = NOT_UNITS[rec.pop("unit")]
                if dtype and not rec.get("data type"):
                    rec["data type"] = dtype
                self.stats["units_not_units"] += 1
        unit = rec.get("unit")
        if node not in self.overridden:
            # The pilot metadata is the source of truth: on first contact, drop what the base
            # ontology said about this node's name, database location, unit and range.
            self.overridden.add(node)
            for p in (RDFS.label, EG.storedInDatabaseColumn, EG.storedInDatabaseTable):
                self.stats["replaced_" + p.split("#")[-1]] += len(list(g.objects(node, p)))
                g.remove((node, p, None))
            if unit:
                for p in (EG.unit, EG.unitUCUM, EG.hasUnit):
                    self.stats["replaced_unit"] += len(list(g.objects(node, p)))
                    g.remove((node, p, None))
        g.add((node, RDF.type, EG.Variable))
        g.add((node, RDF.type, OWL.NamedIndividual))
        g.add((node, RDFS.label, Literal(name, lang="en")))
        if file_column != name:
            g.add((node, EG.sourceColumnName, Literal(file_column)))
        loc = self.sensor_map.get((self.current_dataset, str(node).split("#")[-1]))
        if loc:
            if loc.get("lake_sensor_id"):
                g.add((node, EG.dataLakeSensorId, Literal(loc["lake_sensor_id"])))
            if loc.get("lake_sensor_pattern"):
                g.add((node, EG.dataLakeSensorPattern, Literal(loc["lake_sensor_pattern"])))
            if loc.get("lake_column"):
                g.add((node, EG.storedInDatabaseColumn, Literal(loc["lake_column"])))
            g.add((node, EG.dataLakeMatch, Literal(loc.get("match") or "none")))
            self.stats["variables_" + (loc.get("match") or "none")] += 0 if node in self.located else 1
            self.located.add(node)
        if value_format:
            g.add((node, EG.valueFormat, Literal(value_format)))
        if unit:
            q = qudt_unit(unit)
            if q is not None:
                g.add((node, EG.hasUnit, q))
            else:
                self.unmapped_units.add(unit)
        g.add((ds, EG.hasVariable, node))
        for key, val in rec.items():
            if key == "name" or not val:
                continue
            prop = VARIABLE_FIELDS.get(key)
            if prop is None or prop == EG.sourceColumnName:  # written above (only when it differs)
                continue
            if key == "spanish description":
                g.add((node, prop, Literal(val, lang="es")))
            elif prop == DCTERMS.description:
                g.add((node, prop, Literal(val, lang="en")))
            elif prop in NORMALISERS:
                canonical, note = NORMALISERS[prop](val)
                g.add((node, prop, Literal(canonical)))
                if note:
                    g.add((node, EG.aggregationNote, Literal(note)))
            else:
                g.add((node, prop, Literal(val)))


# --------------------------------------------------------------------------------------
# Controlled values: one spelling per meaning (pilots wrote "Float"/"float", "Measured"/"measured", …)
# --------------------------------------------------------------------------------------
DATA_TYPES = {"float": "float", "double": "float", "real": "float", "integer": "integer", "int": "integer",
              "boolean": "boolean", "bool": "boolean", "text": "text", "string": "text",
              "datetime": "timestamp", "timestamp": "timestamp", "date": "date", "geometry": "geometry"}
AGGREGATIONS = {"instantaneous": "instantaneous", "no": "none", "none": "none", "hourly value": "none",
                "mean": "mean", "average": "mean", "sum": "sum", "cumulative": "cumulative"}


def _base(value):
    """lower-case, without a trailing '(…)' qualifier: 'Static (identifier)' -> 'static'"""
    return re.sub(r"\s*\(.*\)\s*$", "", value).strip().lower()


def norm_variable_kind(value):
    return _base(value) or value.lower(), None


def norm_data_type(value):
    b = _base(value)
    return DATA_TYPES.get(b, DATA_TYPES.get(b.split()[0] if b else b, value)), None


def norm_aggregation(value):
    b = _base(value)
    canonical = AGGREGATIONS.get(b)
    if canonical is None:  # 'mean of the preceding hour', 'hourly sum', 'cumulative (daily)', …
        canonical = next((c for k, c in AGGREGATIONS.items() if re.search(r"\b%s\b" % k, value.lower())), None)
    if canonical is None:
        return value.lower(), None
    detail = None if value.strip().lower() in AGGREGATIONS else value  # keep the period/qualifier the pilot wrote
    return canonical, detail


NORMALISERS = {EG.variableKind: norm_variable_kind, EG.dataType: norm_data_type, EG.aggregation: norm_aggregation}


UNIT_SPELLING = {  # spelling variants of the same unit -> one symbol (QUDT / SI style)
    "MWH": "MWh", "kwh": "kWh", "ºC": "°C", "m2": "m²", "m3": "m³", "Bar": "bar", "Year": "year", "Rpm": "rpm", "RPM": "rpm",
    "W/m²K": "W/(m²K)", "kWh/m2": "kWh/m²",
    "kWh/m2/year": "kWh/m²/year", "kwh/m2/year": "kWh/m²/year", "kWh/m²·year": "kWh/m²/year",
    "kWh/m² per year": "kWh/m²/year", "kWh/m² gadā": "kWh/m²/year",     # 'gadā' = Latvian for 'per year'
    "kgCO₂/m²·year": "kg CO₂/m²/year", "t CO₂/year": "tCO₂/year",
    "l/m": "L/min", "m³/m²/h": "m³/(m²h)", "EUR/m2": "EUR/m²",
}
# Texts some pilots put in the unit column that are not units: data types, formats, allowed values.
# -> (data type if the pilot gave none, value format kept in eg:valueFormat)
NOT_UNITS = {
    "Float64": ("float", None), "Integer": ("integer", None), "String": ("text", None),
    "String (e.g., UTF-8)": ("text", "UTF-8"), "yes/no": ("boolean", None),
    "Date": ("date", None), "date": ("date", None), "Data": ("date", None), "DD.MM.YYYY": ("date", "DD.MM.YYYY"),
    "Datetime (Mon, Jun 2, 2025, 01:00)": ("timestamp", "Mon, Jun 2, 2025, 01:00"),
    "Polygon": ("geometry", "Polygon"), "Polygon Z / MultiPolygon Z": ("geometry", "Polygon Z / MultiPolygon Z"),
    "List of geometry types": ("text", "list of geometry types"),
    "Float64 array [xmin, ymin, xmax, ymax]": ("float", "array [xmin, ymin, xmax, ymax]"),
    "EPSG code (EPSG:3059)": ("text", "EPSG code, e.g. EPSG:3059"),
    "DBF": (None, "DBF file"), "SHX binary": (None, "SHX binary file"),
    "A / B/ C": ("text", "one of A / B / C"), "I / II / III": ("text", "one of I / II / III"),
    "ranges": (None, "ranges"), "varies": (None, "varies"),
    "Depending on the abbreviation": (None, "unit given by the ABBREVIATION column"),
}
# 'mbarg' (gauge pressure) and 'mBar' are different quantities and stay as delivered.
QUDT = "http://qudt.org/vocab/unit/"
UNIT_MAP = {  # metadata unit text -> QUDT unit id (only unambiguous ones)
    "°c": "DEG_C", "ºc": "DEG_C", "c": "DEG_C", "%": "PERCENT", "w": "W", "kw": "KiloW", "mw": "MegaW",
    "kwh": "KiloW-HR", "mwh": "MegaW-HR", "wh": "W-HR", "v": "V", "a": "A", "bar": "BAR",
    "mbar": "MilliBAR", "mbarg": "MilliBAR", "pa": "PA", "kpa": "KiloPA", "m/s": "M-PER-SEC",
    "w/m²": "W-PER-M2", "w/m2": "W-PER-M2", "m³": "M3", "m3": "M3", "l": "L", "l/min": "L-PER-MIN",
    "l/h": "L-PER-HR", "m3/h": "M3-PER-HR", "m³/h": "M3-PER-HR", "g/h": "GM-PER-HR", "kg/h": "KiloGM-PER-HR",
    "us/cm": "MicroS-PER-CentiM", "µs/cm": "MicroS-PER-CentiM", "rpm": "REV-PER-MIN", "s": "SEC",
    "h": "HR", "min": "MIN", "hz": "HZ", "m2": "M2", "m²": "M2", "mm": "MilliM", "m": "M",
    "µg/m³": "MicroGM-PER-M3", "ug/m3": "MicroGM-PER-M3", "year": "YR", "°": "DEG", "db": "DeciB",
    "km/h": "KiloM-PER-HR", "ppm": "PPM", "w/m²k": "W-PER-M2-K", "w/m²k": "W-PER-M2-K",
    "w/m²k": "W-PER-M2-K", "kwh/m2": "KiloW-HR-PER-M2", "kwh/m²": "KiloW-HR-PER-M2",
    # checked against qudt.org/vocab/unit (2026-11-13); the CO₂ units map to the mass-per-x unit,
    # the text unit (eg:unit) keeps "CO₂"
    "count": "NUM", "1/h": "PER-HR", "eur": "CCY_EUR", "eur/m²": "CCY_EUR-PER-M2", "€/mwh": "CCY_EUR-PER-MegaW-HR",
    "kgco₂/m²": "KiloGM-PER-M2", "tco₂/year": "TONNE-PER-YR",
}
# no QUDT unit exists for: kWh/m²/year, kWh/year, m³/(m²h), kg CO₂/m²/year, kgCO₂/MWh, Wp, LEL, NL, NL/h,
# NL/min, Nm3/h (normal litres / cubic metres), step, word -> text unit only


def qudt_unit(text):
    key = re.sub(r"\s+", "", text.strip().lower()).replace("(", "").replace(")", "")
    key = {"w/(m²k)": "w/m²k"}.get(key, key)
    q = UNIT_MAP.get(key)
    return URIRef(QUDT + q) if q else None


PILOT_SOURCES = [
    # (reader, args, namespace, pilot class, PostgreSQL schema used for the default table names)
    (read_ciemat, ("CIEMAT Metadata.xlsx",), CIEMAT, MP.CIEMAT, "ciemat"),
    (read_ber, ("BER_metadata.xlsx",), BER, MP.BER, "ber"),
    (read_simple, ("CEA Metadata.xlsx", "Dataset", "Variable"), CEA, MP.CEA, "cea"),
    (read_simple, ("CARTIF_H2_Metadata.xlsx", "Dataset metadata", "Variable metadata"), CARTIF, MP.CARTIF, "cartif"),
    (read_rea, ("REA - Metadata.xlsx",), REA, MP.REA, "rea"),
    (read_engreen, ("RIN_P011_EnergyGuard_Metadata_ENGREEN_261106.xlsx",), ENGREEN, MP.ENGREEN, "engreen"),
]
TABLES_CSV = MAPPINGS_DIR / "dataset_tables.csv"   # written by utils/ontology/discover_data_lake.py
SENSOR_CSV = MAPPINGS_DIR / "sensor_map.csv"       # written by utils/ontology/discover_data_lake.py
# the server address is kept out of the public ontology on purpose
DATA_LAKE_SERVER = "EnergyGuard data lake (operated by CARTIF)"


def load_tables():
    if not TABLES_CSV.exists():
        return {}
    with TABLES_CSV.open(newline="", encoding="utf-8") as f:
        return {r["dataset"]: r for r in csv.DictReader(f) if r.get("dataset")}


def load_sensor_map():
    if not SENSOR_CSV.exists():
        return {}
    with SENSOR_CSV.open(newline="", encoding="utf-8") as f:
        return {(r["dataset"], r["variable"]): r for r in csv.DictReader(f)}


def add_metadata(g, stats):
    declare_vocab(g)
    delivered_rows = read_delivered(META_DIR / "Metadata Format.xlsx")
    delivered = {norm(d.get("dataset name"))[:40]: d for d in delivered_rows if d.get("dataset name")}
    w = MetadataWriter(g, stats)
    # table names: ontology/mappings/dataset_tables.csv wins; new datasets get a default name
    configured = load_tables()
    w.sensor_map = load_sensor_map()
    for reader, args, ns, pilot_cls, schema in PILOT_SOURCES:
        path = META_DIR / args[0]
        if not path.exists():
            print(f"  ! missing {path.name}, skipped", file=sys.stderr)
            continue
        for d in reader(path, *args[1:]):
            ds = w.dataset(ns, pilot_cls, d["fields"], delivered, schema, configured)
            w.claimed = set()  # per dataset (BER's two datasets share the same signal nodes)
            names = {v["name"] for v in d["variables"]}
            for rec in d["variables"]:
                w.variable(ns, ds, rec, d["scope"], names - {rec["name"]})
    # RDN has no metadata workbook yet: register its delivered datasets by name
    for d in delivered_rows:
        if (d.get("pilot") or "").upper() == "RDN" and d.get("dataset name"):
            w.dataset(RDN, MP.RDN, {"title": d["dataset name"]}, {}, "rdn", configured)
    stats["unmapped_units"] = sorted(w.unmapped_units)
    g.bind("rdn", RDN)
    g.bind("mp", MP)
    g.bind("dcat", DCAT)
    g.bind("dcterms", DCTERMS)
    g.bind("saref", "https://saref.etsi.org/core/", override=True)
    g.bind("s4ener", "https://saref.etsi.org/saref4ener/", override=True)


# --------------------------------------------------------------------------------------
# 5. Metadata is the truth: drop base content the metadata does not back
# --------------------------------------------------------------------------------------
# Pilots whose sensor list is delivered in pilot_metadata/. (RDN has no workbook yet,
# Riga and EnGreen base ontologies carry no sensor/sample-dataset individuals.)
PRUNE_NS = [CIEMAT, BER, CEA, CARTIF]


def _remove_node(g, node, removed):
    """Remove a node everywhere (as subject and object), including blank nodes it owns."""
    owned = [o for o in g.objects(node, None) if isinstance(o, BNode)]
    g.remove((node, None, None))
    g.remove((None, None, node))
    removed.add(node)
    for b in owned:
        if (None, None, b) not in g:
            _remove_node(g, b, removed)


# references in the source ontologies to records under another name (ENGREEN mixes 'User' and 'User1')
REFERENCE_ALIASES = {BASE + "/engreen#MeasurementSeries_User1": BASE + "/engreen#MeasurementSeries_User"}


def repair_references(g, stats):
    """Point aliased references at the real record, declare used-but-undeclared pilot classes, drop
    references to records that exist nowhere, and label timestamp individuals by their value."""
    for old, new in REFERENCE_ALIASES.items():
        for s, p in list(g.subject_predicates(URIRef(old))):
            g.remove((s, p, URIRef(old)))
            g.add((s, p, URIRef(new)))
            stats["repaired_aliases"] += 1
    pilot_ns = tuple(f"{BASE}/{p}#" for p in ("rdn", "ciemat", "ber", "cea", "cartif", "rea", "engreen"))
    in_pilot = lambda x: isinstance(x, URIRef) and str(x).startswith(pilot_ns)
    subjects = set(g.subjects())
    for s, p, o in list(g):
        if not in_pilot(o) or o in subjects:
            continue
        if p == RDF.type:   # used as a class but never declared, e.g. engreen:Timestamp
            g.add((o, RDF.type, OWL.Class))
            g.add((o, RDFS.label, Literal(re.sub(r"(?<=[a-z])(?=[A-Z])", " ", str(o).split("#")[-1]))))
            subjects.add(o)
            stats["declared_classes"] += 1
            stats.setdefault("declared_list", []).append(str(o).split("/ontology/")[1])
        else:
            g.remove((s, p, o))
            stats["pruned_dangling_refs"] += 1
    ts_class = URIRef(BASE + "/engreen#Timestamp")
    for ts in g.subjects(RDF.type, ts_class):
        value = g.value(ts, URIRef(BASE + "/engreen#dateTime"))
        if value is not None and g.value(ts, RDFS.label) is None:
            g.add((ts, RDFS.label, Literal(str(value).replace("T", " ")[:16])))


def prune_to_metadata(g, stats):
    removed = set()
    linked = set(g.objects(None, MP.hasDataset))
    for ns in PRUNE_NS:
        in_ns = lambda x: isinstance(x, URIRef) and str(x).startswith(str(ns))
        schema = {OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty, OWL.Ontology}
        groups_with_members = {s for s in g.subjects(EG.hasMeasurement, None) if in_ns(s)}
        for s in sorted({s for s in g.subjects() if in_ns(s)}):
            types = set(g.objects(s, RDF.type))
            if types & schema or EG.Variable in types or s in linked:
                continue
            if (s, EG.storedInDatabaseTable, None) in g or (s, EG.storedInDatabaseColumn, None) in g:
                kind = "sensors"   # (a) sensor/column of an old sample dataset, not in the metadata
            elif s not in linked and (DCAT.Dataset in types or ns["Dataset"] in types):
                kind = "datasets"  # (b) the old sample dataset itself
            else:
                continue
            stats["pruned_" + kind] += 1
            stats["pruned_list"].append(str(s).split("/ontology/")[1])
            _remove_node(g, s, removed)
        # (c) references to pilot nodes that exist nowhere (not in the metadata either)
        subjects = set(g.subjects())
        for s, p, o in list(g):
            if in_ns(s) and in_ns(o) and o not in subjects and p != RDF.type:
                g.remove((s, p, o))
                stats["pruned_dangling_refs"] += 1
        # (d) measurement groups that had members before and have none left
        for s in sorted(groups_with_members):
            if (s, EG.hasMeasurement, None) not in g:
                stats["pruned_groups"] += 1
                stats["pruned_list"].append(str(s).split("/ontology/")[1])
                _remove_node(g, s, removed)
    return removed


# --------------------------------------------------------------------------------------
# 6. Simplify the structure
# --------------------------------------------------------------------------------------
PILOT_NAMESPACES = {pre: ns for pre, ns in EG_PREFIXES.items() if pre not in ("eg", "mp")}
METADATA_PILOTS = {"ciemat", "ber", "cea", "cartif"}  # sensors fully described by the metadata
SCHEMA_KINDS = (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty)


def _pilot_of(term):
    s = str(term)
    for pre, ns in PILOT_NAMESPACES.items():
        if s.startswith(ns):
            return pre
    return None


def _rewrite(g, mapping):
    for s, p, o in list(g):
        s2, p2, o2 = mapping.get(s, s), mapping.get(p, p), mapping.get(o, o)
        if (s2, p2, o2) != (s, p, o):
            g.remove((s, p, o))
            g.add((s2, p2, o2))


def _keep_one(g, s, p):
    """Keep a single value (the most frequent spelling, then alphabetical) for a merged term."""
    vals = sorted(g.objects(s, p), key=str)
    if len(vals) > 1:
        keep = max(vals, key=lambda v: (sum(1 for x in vals if str(x) == str(v)), -vals.index(v)))
        for v in vals:
            if v != keep:
                g.remove((s, p, v))


def unify_shared_vocabulary(g, stats):
    """(1) A class/property defined under the same name by several pilots becomes one eg: term."""
    origins = defaultdict(set)
    for kind in SCHEMA_KINDS:
        by_name = defaultdict(list)
        for s in g.subjects(RDF.type, kind):
            pilot = _pilot_of(s)
            if pilot:
                by_name[str(s).split("#")[-1]].append((pilot, s))
            elif kind == OWL.Class and str(s).startswith(str(EG)):
                by_name[str(s).split("#")[-1]].append(("eg", s))  # shared class already exists
        mapping = {}
        for name, copies in by_name.items():
            if len({p for p, _ in copies}) < 2:
                continue
            target = DCAT.Dataset if (kind == OWL.Class and name == "Dataset") else EG[name]
            other_kinds = set(g.objects(target, RDF.type)) & set(SCHEMA_KINDS) - {kind}
            if other_kinds:
                continue
            for pilot, s in copies:
                if s != target:
                    mapping[s] = target
                origins[target].add(pilot)
            stats["unified_" + str(kind).split("#")[-1]] += 1
            stats["unified_copies"] += len(copies)
        domains = {t: {mapping.get(o, o) for s in mapping if mapping[s] == t for o in g.objects(s, RDFS.domain)}
                   for t in set(mapping.values())}
        ranges = {t: {mapping.get(o, o) for s in mapping if mapping[s] == t for o in g.objects(s, RDFS.range)}
                  for t in set(mapping.values())}
        # a pilot may *use* a class it never defined (BER types one sensor ber:HydrogenMeasurement):
        # point such references at the shared class when one exists
        if kind == OWL.Class:
            shared = set(mapping.values())
            for o in set(g.objects(None, RDF.type)):
                if _pilot_of(o) and o not in mapping and (o, None, None) not in g:
                    target = EG[str(o).split("#")[-1]]
                    if target in shared:
                        mapping[o] = target
                        stats["unified_undefined_type_refs"] += 1
        _rewrite(g, mapping)
        for target in set(mapping.values()):
            for p, vals in ((RDFS.domain, domains[target]), (RDFS.range, ranges[target])):
                g.remove((target, p, None))
                if len(vals) == 1:  # keep a domain/range only when every pilot agreed …
                    g.add((target, p, next(iter(vals))))
            # … and only a domain the actual data respects (eg:unit is also used on REA/ENGREEN
            # variables; a wrong domain would make reasoners re-classify them)
            for dom in list(g.objects(target, RDFS.domain)):
                if any((s, RDF.type, dom) not in g for s in g.subjects(target, None)):
                    g.remove((target, RDFS.domain, dom))
            if target == DCAT.Dataset:  # don't restate the external DCAT class
                for p in (RDFS.subClassOf, RDFS.comment, RDFS.label):
                    g.remove((target, p, None))
                g.add((target, RDFS.label, Literal("Dataset", lang="en")))
            g.remove((target, RDFS.subClassOf, target))
            g.remove((target, RDFS.subPropertyOf, target))
            g.remove((target, OWL.equivalentProperty, target))
            g.remove((target, OWL.equivalentClass, target))
            _keep_one(g, target, RDFS.label)
            _keep_one(g, target, RDFS.comment)
    return origins


def drop_unused_properties(g, stats, origins):
    """(2) Properties declared by the metadata-backed pilots that no data uses."""
    used = set(g.predicates())
    for kind in (OWL.ObjectProperty, OWL.DatatypeProperty):
        for prop in sorted(set(g.subjects(RDF.type, kind))):
            if prop in used:
                continue
            src = origins.get(prop) or ({_pilot_of(prop)} if _pilot_of(prop) else None)
            if src and src <= METADATA_PILOTS:
                g.remove((prop, None, None))
                g.remove((None, None, prop))
                stats["dropped_unused_properties"] += 1


def drop_plumbing(g, stats):
    """(3) Pilot membership encoded as sub-class/sub-property of pilot classes, one-off sample
    links, and the headers of the original per-pilot files. The namespace already says the pilot."""
    for s, p, o in list(g):
        if (p in (RDFS.subClassOf, RDFS.subPropertyOf) and str(o).startswith(str(MP))
                and not str(s).startswith(str(MP))):
            g.remove((s, p, o))
            stats["dropped_membership_links"] += 1
    for p in (MP.hasClassEntity, MP.hasPropertyEntity, MP.hasIndividualEntity):
        stats["dropped_membership_links"] += len(list(g.subject_objects(p)))
        g.remove((None, p, None))
        g.remove((p, None, None))
    main_header = URIRef(BASE + "/merged-pilots")
    for h in sorted(set(g.subjects(RDF.type, OWL.Ontology))):
        if h != main_header:
            g.remove((h, None, None))
            g.remove((None, None, h))
            stats["dropped_headers"] += 1
    g.remove((main_header, RDFS.label, None))
    g.add((main_header, RDFS.label, Literal("EnergyGuard Ontology (all pilots)", lang="en")))


def simplify(g, stats):
    origins = unify_shared_vocabulary(g, stats)
    drop_unused_properties(g, stats, origins)
    drop_plumbing(g, stats)


# --------------------------------------------------------------------------------------
# 7. Measurement classes for time-series variables
# --------------------------------------------------------------------------------------
# One shared eg: class per measurement type. A variable's class is decided from the pilot
# metadata first (unit, then sensor type, then variable kind); the data lake's own sensor type
# is used only when the metadata says nothing. Disagreements are reported, metadata wins.
MEASUREMENT_TYPES = {  # class local name -> label
    "TemperatureMeasurement": "Temperature Measurement", "PressureMeasurement": "Pressure Measurement",
    "FlowMeasurement": "Flow Measurement", "PowerMeasurement": "Power Measurement",
    "EnergyMeasurement": "Energy Measurement", "CurrentMeasurement": "Current Measurement",
    "VoltageMeasurement": "Voltage Measurement", "SpeedMeasurement": "Speed Measurement",
    "SolarRadiationMeasurement": "Solar Radiation Measurement", "CompositionMeasurement": "Composition Measurement",
    "LevelMeasurement": "Level Measurement", "VolumeMeasurement": "Volume Measurement",
    "TimerMeasurement": "Timer Measurement", "EfficiencyMeasurement": "Efficiency Measurement",
    "StateOfChargeMeasurement": "State Of Charge Measurement", "StateMeasurement": "State Measurement",
    "ControlSignalMeasurement": "Control Signal Measurement", "CloudCoverMeasurement": "Cloud Cover Measurement",
}
# What each measurement type means. Written onto the shared eg: classes after classification, replacing the
# pilot-specific comments some of them arrived with (those named one pilot's sensors).
MEASUREMENT_TYPE_DEFINITIONS = {
    "Temperature": "temperature readings (°C).",
    "Pressure": "pressure readings (bar, mbar, Pa).",
    "Flow": "flow rates of gases or liquids (L/min, m³/h, kg/h).",
    "Power": "electrical or thermal power (W, kW, MW).",
    "Energy": "energy values (Wh, kWh, MWh): consumed, produced or cumulative.",
    "Current": "electric current (A).",
    "Voltage": "electric voltage (V).",
    "Speed": "speeds (m/s, rpm).",
    "SolarRadiation": "solar irradiance (W/m²).",
    "Composition": "gas or fluid composition (ppm, LEL).",
    "Level": "fill level of a tank.",
    "Volume": "volumes (m³, L).",
    "Timer": "elapsed or counted time (s, h), such as hour counters.",
    "Efficiency": "efficiency indicators.",
    "StateOfCharge": "state of charge of a battery (%).",
    "State": "on/off or discrete operating state, status and alarm signals.",
    "ControlSignal": "control outputs and commands sent to equipment.",
    "CloudCover": "cloud cover (%).",
    "Hydrogen": "hydrogen-related data: flow, pressure or storage.",
}
MEASUREMENT_COMMENT = ("A time-stamped reading from a sensor or system (numeric, state or signal). Its subclasses are the "
                       "measurement types (Temperature, Pressure, ...); a variable that is a measurement is an instance of one.")
# columns of a time-series dataset that are not measurements get their own classes (under eg:Variable)
COLUMN_CLASSES = {"TimeColumn": ("Time Column", "The time stamp column of a time-series dataset."),
                  "IdentifierColumn": ("Identifier Column", "A column that identifies the measured object (address, cadastre number, id).")}
IDENTIFIER_NAME = re.compile(r"^\s*(adrese|address|kadastra|cadastral|.*\bid)\b", re.I)
CLASS_OVERRIDES = {  # (variable local name) -> (class, why); only where the metadata says it in prose
    "Buildings_monthly_heat_series_ARCGIS_Server__01_2021_current_month_current_year":
        ("Energy", "metadata: the dataset holds the monthly heating consumption, 'based on the previous dataset' (Heating 2017-2024, MWh)"),
}
UNIT_CLASS = {  # metadata unit (normalised) -> class
    "°c": "Temperature", "ºc": "Temperature", "c": "Temperature",
    "bar": "Pressure", "mbar": "Pressure", "mbarg": "Pressure", "pa": "Pressure", "kpa": "Pressure",
    "w": "Power", "kw": "Power", "mw": "Power",
    "wh": "Energy", "kwh": "Energy", "mwh": "Energy",
    "a": "Current", "v": "Voltage",
    "l/m": "Flow", "l/min": "Flow", "nl/min": "Flow", "nl/h": "Flow", "m3/h": "Flow", "m³/h": "Flow",
    "nm3/h": "Flow", "g/h": "Flow", "kg/h": "Flow",
    "m/s": "Speed", "km/h": "Speed", "rpm": "Speed",
    "w/m²": "SolarRadiation", "w/m2": "SolarRadiation",
    "ppm": "Composition", "lel": "Composition",
    "m³": "Volume", "m3": "Volume", "l": "Volume", "nl": "Volume",
    "s": "Timer", "h": "Timer",
    "step": "State", "word": "State",
}
SENSOR_TYPE_CLASS = [  # keyword in the metadata sensor type -> class (first match wins)
    ("temperature", "Temperature"), ("pressure", "Pressure"), ("flow", "Flow"), ("composition", "Composition"),
    ("level", "Level"), ("current", "Current"), ("voltage", "Voltage"), ("soc", "StateOfCharge"),
    ("pyranometer", "SolarRadiation"), ("anemometer", "Speed"), ("status", "State"), ("power", "Power"),
    ("cloud", "CloudCover"),
]
KIND_CLASS = {"state": "State", "alarm": "State", "output": "ControlSignal", "setpoint": "ControlSignal"}
LAKE_CLASS = {  # data lake sensor type -> class
    "Temperature": "Temperature", "IndoorTemperature": "Temperature", "OutdoorTemperature": "Temperature",
    "Pressure": "Pressure", "Flow": "Flow", "Power": "Power", "Electricity": "Energy", "ThermalEnergy": "Energy",
    "Current": "Current", "Voltage": "Voltage", "Speed": "Speed", "SolarRadiation": "SolarRadiation",
    "Volume": "Volume", "Status": "State", "Relay": "State", "Counter": "Timer", "Efficiency": "Efficiency",
    "SoC": "StateOfCharge", "CO2": "Composition", "Gas": "Composition", "CloudPercentage": "CloudCover",
}
CLASS_REPORT = REPORTS_DIR / "variable_classes_report.csv"


def _class_from_metadata(unit, sensor_type, kind, name=""):
    u = re.sub(r"\s+", "", (unit or "").lower())
    if u in UNIT_CLASS:
        return UNIT_CLASS[u], f"unit {unit}"
    if re.search(r"\bsoc\b", (name or "").lower()):
        return "StateOfCharge", f"name {name}"
    st = (sensor_type or "").lower()
    for key, cls in SENSOR_TYPE_CLASS:
        if re.search(r"\b%s\b" % key, st):
            return cls, f"sensor type {sensor_type}"
    if (kind or "") in KIND_CLASS:
        return KIND_CLASS[kind], f"variable kind {kind}"
    return None, ""


def classify_variables(g, stats, sensor_map, report_rows):
    measurement_classes = {s for s in g.transitive_subjects(RDFS.subClassOf, EG.Measurement)}
    for pilot_cls, ds in sorted(g.subject_objects(MP.hasDataset)):
        layouts = {str(o) for o in g.objects(ds, EG.tableLayout)}
        dtype = " ".join(str(o) for o in g.objects(ds, EG.datasetType)).lower()
        if "long" not in layouts and "time series" not in dtype:
            continue  # static/GIS datasets: their columns are attributes, not measurements
        for v in sorted(g.objects(ds, EG.hasVariable)):
            types = set(g.objects(v, RDF.type))
            if types & measurement_classes or any(str(t).endswith("Measurement") and "Group" not in str(t) for t in types):
                continue
            kind = str(next(g.objects(v, EG.variableKind), ""))
            label = str(next(g.objects(v, RDFS.label), ""))
            column_cls = "TimeColumn" if kind == "timestamp" or (v, EG.dataLakeMatch, Literal("timestamp")) in g \
                else ("IdentifierColumn" if IDENTIFIER_NAME.match(label) else None)
            if column_cls:
                cls = EG[column_cls]
                g.add((v, RDF.type, cls))
                if (cls, RDF.type, OWL.Class) not in g:
                    g.add((cls, RDF.type, OWL.Class))
                    g.add((cls, RDFS.subClassOf, EG.Variable))
                    g.add((cls, RDFS.label, Literal(COLUMN_CLASSES[column_cls][0], lang="en")))
                    g.add((cls, RDFS.comment, Literal(COLUMN_CLASSES[column_cls][1], lang="en")))
                stats["classified_columns"] += 1
                report_rows.append({"pilot": str(pilot_cls).split("#")[-1], "dataset": str(ds).split("#")[-1],
                                    "variable": str(v).split("#")[-1], "class": column_cls,
                                    "decided_by": "time column" if column_cls == "TimeColumn" else f"name {label}",
                                    "metadata_says": "", "lake_says": "", "conflict": ""})
                continue
            if kind == "static":
                continue
            meta_cls, why = _class_from_metadata(str(next(g.objects(v, EG.unit), "")),
                                                 str(next(g.objects(v, EG.sensorType), "")), kind,
                                                 str(next(g.objects(v, RDFS.label), "")))
            row = sensor_map.get((str(ds).split("#")[-1], str(v).split("#")[-1]), {})
            lake_types = {x for x in (row.get("lake_sensor_type") or "").split("/") if x}
            lake_classes = {LAKE_CLASS[x] for x in lake_types if x in LAKE_CLASS}
            lake_cls = next(iter(lake_classes)) if len(lake_classes) == 1 else None
            chosen, source = (meta_cls, "metadata: " + why) if meta_cls else \
                ((lake_cls, "data lake sensor type " + "/".join(sorted(lake_types))) if lake_cls else (None, ""))
            if not chosen and str(v).split("#")[-1] in CLASS_OVERRIDES:
                chosen, source = CLASS_OVERRIDES[str(v).split("#")[-1]]
                meta_cls = chosen
            if not chosen and str(next(g.objects(v, EG.dataType), "")) == "boolean":
                chosen, source = "State", "metadata: data type boolean (an on/off signal)"
                meta_cls = chosen
            if meta_cls and lake_cls and meta_cls != lake_cls:
                stats["class_conflicts"] += 1
            if chosen:
                cls = EG[chosen + "Measurement"]
                g.add((v, RDF.type, cls))
                if (cls, RDF.type, OWL.Class) not in g:
                    g.add((cls, RDF.type, OWL.Class))
                    g.add((cls, RDFS.subClassOf, EG.Measurement))
                    g.add((cls, RDFS.label, Literal(MEASUREMENT_TYPES[chosen + "Measurement"], lang="en")))
                    stats["classes_added"] += 1
                stats["classified_from_" + ("metadata" if meta_cls else "lake")] += 1
            else:
                stats["not_classified"] += 1
            report_rows.append({
                "pilot": str(pilot_cls).split("#")[-1], "dataset": str(ds).split("#")[-1],
                "variable": str(v).split("#")[-1], "class": chosen + "Measurement" if chosen else "",
                "decided_by": source, "metadata_says": meta_cls or "", "lake_says": "/".join(sorted(lake_types)),
                "conflict": "yes" if (meta_cls and lake_cls and meta_cls != lake_cls) else "",
            })


def describe_measurement_types(g):
    """Give eg:Measurement and each shared measurement type one consistent comment ('Measurement type: ...')."""
    def set_comment(cls, text):
        for old in list(g.objects(cls, RDFS.comment)):
            g.remove((cls, RDFS.comment, old))
        g.add((cls, RDFS.comment, Literal(text, lang="en")))
    set_comment(EG.Measurement, MEASUREMENT_COMMENT)
    for short, definition in MEASUREMENT_TYPE_DEFINITIONS.items():
        cls = EG[short + "Measurement"]
        if (cls, RDF.type, OWL.Class) in g:
            set_comment(cls, "Measurement type: " + definition)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--base", type=Path, default=BASE_OWL)
    ap.add_argument("--out", type=Path, default=OUT_OWL)
    ap.add_argument("--check", action="store_true", help="build and report, don't write")
    a = ap.parse_args()

    # rdflib logs a full traceback for literals that don't match their datatype (e.g. an
    # xsd:date "end" in the EnGreen source); clean_base drops them, so keep the log quiet.
    logging.getLogger("rdflib.term").setLevel(logging.CRITICAL)
    stats = defaultdict(int)
    base = rdflib.Graph()
    base.parse(a.base, format="xml")
    g = clean_base(base, stats)
    n_base = len(g)
    add_metadata(g, stats)
    stats["pruned_list"] = []
    prune_to_metadata(g, stats)
    repair_references(g, stats)
    class_report = []
    sensor_map = load_sensor_map()
    classify_variables(g, stats, sensor_map, class_report)
    simplify(g, stats)
    describe_measurement_types(g)   # after simplify: it merges pilot classes (and their comments) into the shared ones
    add_standards_layer(g, stats, MEASUREMENT_TYPE_DEFINITIONS, sensor_map)   # SOSA/QUDT, DCAT, PROV/DQV, GeoSPARQL, SKOS

    print(f"base triples: {len(base)}  after clean-up: {n_base}  final: {len(g)}")
    for k in ("eg_ref", "struct_pred", "mojibake", "file_iri", "curie", "qudt_units_fixed"):
        print(f"  clean-up {k}: {stats[k]}")
    for k in ("datasets", "vars_matched", "vars_enriched", "vars_new",
              "replaced_label", "replaced_storedInDatabaseColumn", "replaced_storedInDatabaseTable",
              "replaced_unit", "datasets_located", "variables_exact", "variables_normalised",
              "variables_pattern", "variables_column", "variables_timestamp", "variables_inferred", "variables_manual",
              "variables_none", "unmapped_units",
              "pruned_sensors", "pruned_datasets", "pruned_groups", "pruned_dangling_refs",
              "unified_Class", "unified_ObjectProperty", "unified_DatatypeProperty", "unified_copies",
              "unified_undefined_type_refs", "dropped_unused_properties", "dropped_membership_links", "dropped_headers",
              "classified_from_metadata", "classified_from_lake", "classified_columns", "not_classified", "class_conflicts",
              "classes_added", "units_not_units", "repaired_aliases", "declared_classes",
              "observable_properties", "quantity_kind_links", "variables_sensor", "variables_related_to_property",
              "classes_deprecated", "measurement_parents_removed", "platforms", "variables_hosted",
              "datasets_with_period", "datasets_with_resolution", "datasets_with_frequency", "datasets_with_licence",
              "distributions", "datasets_outside_tree", "geospatial_datasets", "datasets_with_crs", "lake_links_with_provenance",
              "range_unit_inconsistencies"):
        print(f"  metadata {k}: {stats[k]}")
    if a.check:
        print("  pruned:", ", ".join(stats["pruned_list"]))
        print("  declared classes:", ", ".join(stats.get("declared_list", [])))
    if not a.check:
        CLASS_REPORT.parent.mkdir(parents=True, exist_ok=True)
        with CLASS_REPORT.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["pilot", "dataset", "variable", "class", "decided_by",
                                              "metadata_says", "lake_says", "conflict"])
            w.writeheader()
            w.writerows(class_report)
        final = rdflib.Graph()
        for prefix, ns in g.namespaces():
            final.bind(prefix, ns, override=True)
        for t in sorted(g, key=lambda t: tuple(f"{type(x).__name__}{x}" for x in t)):
            final.add(t)
        xml = final.serialize(format="pretty-xml", encoding="utf-8").decode("utf-8")
        # declare every EnergyGuard prefix in the header, even those only used inside IRIs,
        # so readers (and n10s) see readable prefixes for all pilot namespaces
        declared = set(re.findall(r'xmlns:([A-Za-z0-9_]+)=', xml.split(">", 2)[1]))
        extra = "".join(f'\n  xmlns:{pre}="{ns}"' for pre, ns in sorted(EG_PREFIXES.items()) if pre not in declared)
        xml = xml.replace("<rdf:RDF", "<rdf:RDF" + extra, 1)
        a.out.write_bytes(xml.encode("utf-8"))
        print(f"wrote {a.out}")


if __name__ == "__main__":
    # rdflib's serializer walks hash-ordered sets: pin the hash seed so the same inputs
    # always produce a byte-identical file (clean git diffs).
    if os.environ.get("PYTHONHASHSEED") != "0":
        os.environ["PYTHONHASHSEED"] = "0"
        os.execv(sys.executable, [sys.executable] + sys.argv)
    main()
