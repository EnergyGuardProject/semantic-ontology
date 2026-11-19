#!/usr/bin/env python3
"""ONE-TIME import: turn the generated ontology into the curated catalogue files.

This is not part of the normal workflow. It was run once to create ontology/catalogue/*.ttl from the generated
ontology/all_pilots.owl; from then on those Turtle files are the source of truth and are edited by hand
(utils/ontology/workbook_diff.py shows what a new partner workbook would change).

It keeps only the catalogue (pilots, datasets, variables) and the standard-based facts about them, and drops what the
catalogue does not need: the pilots' original domain vocabularies, the measurement groups, and every property that is
now expressed with a standard term.

Usage: python3 utils/ontology/import_once.py [--from ontology/all_pilots.owl]
"""
import argparse
import re
from collections import defaultdict
from pathlib import Path

import rdflib
from rdflib import BNode, Literal, Namespace, URIRef
from rdflib.namespace import DCAT, DCTERMS, FOAF, OWL, PROV, RDF, RDFS, SKOS, XSD

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://www.energyguard.eu/ontology"
EG = Namespace(BASE + "#")
MP = Namespace(BASE + "/merged-pilots#")
PROP = Namespace(BASE + "/property#")
SOSA = Namespace("http://www.w3.org/ns/sosa/")
DQV = Namespace("http://www.w3.org/ns/dqv#")
QUDT = Namespace("http://qudt.org/schema/qudt/")
SCHEMA = Namespace("http://schema.org/")
CSVW = Namespace("http://www.w3.org/ns/csvw#")
GEOSPARQL = Namespace("http://www.opengis.net/ont/geosparql#")
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")

PILOTS = ["RDN", "CIEMAT", "BER", "CEA", "CARTIF", "REA", "ENGREEN"]
# properties copied unchanged from a dataset / a variable
DATASET_KEEP = {DCTERMS.title, DCTERMS.description, DCTERMS.publisher, DCTERMS.spatial, DCTERMS.temporal, DCTERMS.license,
                DCTERMS.accessRights, DCTERMS.conformsTo, DCTERMS.accrualPeriodicity, DCAT.contactPoint,
                DCAT.temporalResolution, DCAT.distribution, EG.systemDescribed, EG.sourceSystem, EG.timeZone,
                EG.missingValues, EG.fileFormat, EG.recordCount, EG.hasVariable}
VARIABLE_KEEP = {RDFS.label, DCTERMS.description, EG.variableKind, EG.aggregation, EG.signConvention, EG.codeList,
                 EG.dataType, EG.sampling, EG.recordThreshold, EG.decimals, EG.dataLakeMatch, EG.dataLakeSensorId,
                 EG.dataLakeSensorPattern, EG.storedInDatabaseColumn, SOSA.observes, EG.relatesToProperty,
                 SOSA.isHostedBy, EG.hasLakeLink, DQV.hasQualityMeasurement}
KEPT_TYPES = {EG.Variable, EG.TimeColumn, EG.IdentifierColumn, SOSA.Sensor, DCAT.Dataset, GEOSPARQL.FeatureCollection}
SHARED_NODES = {EG.OntologyMaintainers, EG.RangeUnitConsistency, EG.ConsistencyDimension, EG.DataLakeService}


def local(term):
    return str(term).rsplit("#", 1)[-1]


def pilot_of(term):
    m = re.search(r"/ontology/([a-z]+)", str(term))
    return {"rdn": "RDN", "ciemat": "CIEMAT", "ber": "BER", "cea": "CEA", "cartif": "CARTIF", "rea": "REA",
            "engreen": "ENGREEN"}.get(m.group(1)) if m else None


def new_graph():
    g = rdflib.Graph()
    for pre, ns in (("eg", EG), ("mp", MP), ("prop", PROP), ("sosa", SOSA), ("dqv", DQV), ("qudt", QUDT), ("schema", SCHEMA),
                    ("csvw", CSVW), ("dcat", DCAT), ("dcterms", DCTERMS), ("skos", SKOS), ("prov", PROV), ("foaf", FOAF),
                    ("geosparql", GEOSPARQL), ("vcard", VCARD), ("owl", OWL), ("xsd", XSD)):
        g.bind(pre, ns)
    return g


def copy_node(src, dst, node, seen):
    """Copy all triples of a helper node (period, place, distribution, link, ...) and the helper nodes it points to."""
    if node in seen:
        return
    seen.add(node)
    for p, o in src.predicate_objects(node):
        dst.add((node, p, o))
        if isinstance(o, URIRef) and str(o).startswith(BASE) and o not in SHARED_NODES and (o, RDF.type, None) in src \
                and not (o, RDF.type, OWL.Class) in src and not str(o).startswith(str(PROP)) and not str(o).startswith(str(MP)):
            if not any(t in KEPT_TYPES for t in src.objects(o, RDF.type)):
                copy_node(src, dst, o, seen)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--from", dest="src", type=Path, default=ROOT / "ontology" / "all_pilots.owl")
    a = ap.parse_args()
    src = rdflib.Graph(); src.parse(a.src, format="xml")
    out = defaultdict(new_graph)          # pilot -> graph
    shared = new_graph()                  # measurement types, pilots, data lake service
    seen = set()

    datasets = {d: p for p, d in src.subject_objects(MP.hasDataset)}
    pilot_nodes = {}
    for d, p in datasets.items():
        pilot_nodes[str(p).split("#")[-1]] = p
    for d, p in sorted(datasets.items()):
        pilot = str(p).split("#")[-1]
        g = out[pilot]
        for t in src.objects(d, RDF.type):
            if t in KEPT_TYPES:
                g.add((d, RDF.type, t))
        g.add((d, RDF.type, OWL.NamedIndividual))
        for pred in DATASET_KEEP:
            for o in src.objects(d, pred):
                g.add((d, pred, o))
                if isinstance(o, URIRef) and pred in (DCTERMS.spatial, DCTERMS.temporal, DCTERMS.license, DCAT.contactPoint, DCAT.distribution):
                    copy_node(src, g, o, seen)
        for dist in src.objects(d, DCAT.distribution):      # the lake table belongs to the distribution, not the dataset
            for prop in (EG.storedInDatabase, EG.storedInDatabaseTable):
                for o in src.objects(d, prop):
                    g.add((dist, prop, o))
        # fields that have a standard equivalent, but the value could not be parsed into it: keep the text as a note
        for prop, label, parsed in ((EG.timeResolution, "Time resolution", DCAT.temporalResolution),
                                    (EG.updateFrequency, "Update frequency", DCTERMS.accrualPeriodicity),
                                    (EG.temporalCoverage, "Temporal coverage", DCTERMS.temporal)):
            for o in src.objects(d, prop):
                if (d, parsed, None) not in src or prop == EG.updateFrequency:
                    g.add((d, SKOS.note, Literal(f"{label}: {o}", lang="en")))
        for o in src.objects(d, EG.sourceUrl):
            g.add((d, DCAT.landingPage, URIRef(str(o).strip()) if str(o).startswith("http") else Literal(str(o))))
        for o in src.objects(d, EG.datasetType):
            g.add((d, DCTERMS.type, o))
        for o in src.objects(d, EG.notes):
            g.add((d, SKOS.note, o))
        # which catalogue the dataset is in
        g.add((MP[pilot + "_Catalog"], DCAT.dataset, d))

    variables = {}
    for d in datasets:
        for v in src.objects(d, EG.hasVariable):
            variables.setdefault(v, d)
    for v, d in sorted(variables.items()):
        g = out[str(datasets[d]).split("#")[-1]]
        g.add((v, RDF.type, OWL.NamedIndividual))
        for t in src.objects(v, RDF.type):
            if t in KEPT_TYPES:
                g.add((v, RDF.type, t))
        for pred in VARIABLE_KEEP:
            for o in src.objects(v, pred):
                g.add((v, pred, o))
                if pred in (SOSA.isHostedBy, EG.hasLakeLink, DQV.hasQualityMeasurement) and isinstance(o, URIRef):
                    copy_node(src, g, o, seen)
        units = list(src.objects(v, EG.hasUnit))
        for u in units:
            g.add((v, QUDT.hasUnit, u))
        if not units:
            for u in src.objects(v, EG.unit):
                g.add((v, EG.unit, u))
        for lo in src.objects(v, EG.minValue):
            g.add((v, SCHEMA.minValue, lo))
        for hi in src.objects(v, EG.maxValue):
            g.add((v, SCHEMA.maxValue, hi))
        if (v, EG.minValue, None) not in src:
            for r in src.objects(v, EG.validRange):
                g.add((v, SKOS.note, Literal(f"Valid range: {r}", lang="en")))
        for o in src.objects(v, EG.valueFormat):
            g.add((v, CSVW["format"], o))
        for o in src.objects(v, EG.sourceColumnName):
            g.add((v, CSVW["name"], o))
        for o in src.objects(v, EG.sensorId):
            g.add((v, DCTERMS.identifier, o))
        for o in src.objects(v, EG.sensorType):
            g.add((v, DCTERMS.type, o))
        for o in src.objects(v, EG.aggregationNote):
            g.add((v, SKOS.note, o))

    # shared vocabulary: measurement types as observable properties, the lake service, the maintainers, the quality metric
    for prop in src.subjects(RDF.type, SOSA.ObservableProperty):
        for p, o in src.predicate_objects(prop):
            shared.add((prop, p, o))
    for scheme in src.subjects(RDF.type, SKOS.ConceptScheme):
        for p, o in src.predicate_objects(scheme):
            shared.add((scheme, p, o))
    for node in (EG.OntologyMaintainers, EG.RangeUnitConsistency, EG.ConsistencyDimension, EG.DataLakeService):
        for p, o in src.predicate_objects(node):
            if p != DCAT.servesDataset:
                shared.add((node, p, o))
    for ds in datasets:
        if (EG.DataLakeService, DCAT.servesDataset, ds) in src:
            shared.add((EG.DataLakeService, DCAT.servesDataset, ds))
    # pilots: one organisation and one catalogue each, under one root catalogue
    root = MP.EnergyGuard_Catalog
    for t in ((root, RDF.type, DCAT.Catalog), (root, RDF.type, OWL.NamedIndividual),
              (root, DCTERMS.title, Literal("EnergyGuard pilot datasets", lang="en"))):
        shared.add(t)
    for name in PILOTS:
        org, cat = MP[name], MP[name + "_Catalog"]
        label = next((o for o in src.objects(org, RDFS.label)), Literal(name))
        for t in ((org, RDF.type, FOAF.Organization), (org, RDF.type, OWL.NamedIndividual), (org, RDFS.label, label),
                  (cat, RDF.type, DCAT.Catalog), (cat, RDF.type, OWL.NamedIndividual), (cat, DCTERMS.title, Literal(f"{label} datasets", lang="en")),
                  (cat, DCTERMS.publisher, org), (root, DCAT.catalog, cat)):
            shared.add(t)

    outdir = ROOT / "ontology" / "catalogue"
    outdir.mkdir(exist_ok=True)
    for name, g in sorted(out.items()):
        (outdir / f"{name.lower()}.ttl").write_text(g.serialize(format="turtle"), encoding="utf-8")
        print(f"{name:8} {len(g):6} triples -> ontology/catalogue/{name.lower()}.ttl")
    (outdir / "shared.ttl").write_text(shared.serialize(format="turtle"), encoding="utf-8")
    print(f"{'shared':8} {len(shared):6} triples -> ontology/catalogue/shared.ttl")


if __name__ == "__main__":
    main()
