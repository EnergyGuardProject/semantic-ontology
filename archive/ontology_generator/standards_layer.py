"""The standards layer of the EnergyGuard ontology.

Called by build_all_pilots_owl.py after the catalogue and the measurement classes are built. It only ADDS triples (and marks the
old measurement classes as deprecated), so every existing label and query keeps working while the model moves to the
standard patterns:

  1. SOSA / QUDT  a measured variable is a sosa:Sensor that sosa:observes a sosa:ObservableProperty (a skos:Concept linked to
                  a QUDT quantity kind). The measurement classes (eg:TemperatureMeasurement, ...) are deprecated and no longer
                  claimed to be sosa:Observation or saref:Measurement (they are series, not single readings).
  2. SOSA         equipment (the "subsystem" of a variable) becomes a sosa:Platform that hosts the sensor.
  3. DCAT         typed temporal coverage and resolution, update frequency, publisher, contact point, licence, spatial coverage.
  4. DCAT         the lake table is a dcat:Distribution served by one dcat:DataService (the host is not published).
  5. PROV / DQV   provenance of the matches we inferred from the readings, and a quality measurement for ranges written in
                  another unit than the variable's.
  6. (SHACL lives in ontology/shapes.ttl and is checked by utils/ontology/validate_shapes.py.)
  7. GeoSPARQL    datasets with geometries are geo:FeatureCollection and say their coordinate reference system.
  8. SKOS         the measurement types form a skos:ConceptScheme (descriptions already carry @en / @es language tags).
 10. OWL          version, title and licence of the ontology.
"""
import re

from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import DCAT, DCTERMS, FOAF, OWL, PROV, RDF, RDFS, SKOS, XSD

BASE = "https://www.energyguard.eu/ontology"
EG = Namespace(BASE + "#")
MP = Namespace(BASE + "/merged-pilots#")
PROP = Namespace(BASE + "/property#")
SOSA = Namespace("http://www.w3.org/ns/sosa/")
DQV = Namespace("http://www.w3.org/ns/dqv#")
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
GEOSPARQL = Namespace("http://www.opengis.net/ont/geosparql#")
WGS = Namespace("http://www.w3.org/2003/01/geo/wgs84_pos#")
QK = Namespace("http://qudt.org/vocab/quantitykind/")
QUDT = Namespace("http://qudt.org/schema/qudt/")
FREQ = Namespace("http://publications.europa.eu/resource/authority/frequency/")
ACCESS = Namespace("http://publications.europa.eu/resource/authority/access-right/")
EPSG = "http://www.opengis.net/def/crs/EPSG/0/"

ONTOLOGY_VERSION = "1.0.0"
ONTOLOGY_IRI = URIRef(BASE + "/merged-pilots")
LICENCE_IRI = URIRef("https://www.gnu.org/licenses/gpl-3.0.html")   # the repository's licence (LICENSE)

PILOT_NS = re.compile(r"^(https://www\.energyguard\.eu/ontology/(?!merged-pilots|property)[^#]+#)")

# measurement type -> QUDT quantity kinds (only the ones that exist in QUDT and mean the same)
QUANTITY_KINDS = {
    "Temperature": ["Temperature"], "Pressure": ["Pressure"], "Flow": ["VolumeFlowRate", "MassFlowRate"],
    "Power": ["Power"], "Energy": ["Energy"], "Current": ["ElectricCurrent"], "Voltage": ["Voltage"],
    "Speed": ["Speed", "AngularVelocity"], "SolarRadiation": ["Irradiance"], "Volume": ["Volume"],
    "Timer": ["Time"], "Efficiency": ["Efficiency"], "StateOfCharge": ["StateOfCharge"],
}
# these are observed properties of equipment; the others (commands) are only related to a property
NOT_OBSERVED = {"ControlSignal"}
NOT_SENSORS = {"State", "ControlSignal", "Timer"}   # a state / counter is derived, not a physical sensor

EU_FREQUENCY = [(re.compile(r"\b(nightly|daily)\b", re.I), "DAILY"),
                (re.compile(r"\b(one[- ]off|one shot)\b", re.I), "NEVER"),
                (re.compile(r"\bwhen .*change", re.I), "IRREG")]
DATE_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
DATE_EU = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
YEAR = re.compile(r"\b(20\d{2})\b")
DURATION = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(s|sec|seconds?|m|min|minutes?|h|hours?)\b", re.I)
RANGE_UNIT = re.compile(r"[-+]?\d[\d,\.]*\s*(?:–|—|to|-)\s*\+?\s*[-+]?\d[\d,\.]*\s*([A-Za-zµ%/²³°]+)")


def _local(term):
    return str(term).rsplit("#", 1)[-1]


def _ns(term):
    m = PILOT_NS.match(str(term))
    return Namespace(m.group(1)) if m else None


def _slug(text, n=60):
    return re.sub(r"[^A-Za-z0-9]+", "_", str(text)).strip("_")[:n] or "x"


def _label(local):
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", local)


def _typed(g, node, *classes):
    for c in classes:
        g.add((node, RDF.type, c))


def bind_prefixes(g):
    for pre, ns in (("skos", SKOS), ("prov", PROV), ("dqv", DQV), ("vcard", VCARD), ("geosparql", GEOSPARQL),
                    ("quantitykind", QK), ("qudt", QUDT), ("prop", PROP), ("sosa", SOSA), ("foaf", FOAF),
                    ("dcat", DCAT), ("dcterms", DCTERMS)):
        g.bind(pre, ns, override=True)


# ---------------------------------------------------------------------------------------------------- 1, 8
def observable_properties(g, stats, definitions):
    """One sosa:ObservableProperty (and skos:Concept) per measurement type that a variable uses."""
    scheme = EG.MeasurementTypeScheme
    _typed(g, scheme, SKOS.ConceptScheme, OWL.NamedIndividual)
    g.add((scheme, DCTERMS.title, Literal("EnergyGuard measurement types", lang="en")))
    g.add((scheme, DCTERMS.description, Literal(
        "The kinds of quantity or signal an EnergyGuard variable observes. Each one is a sosa:ObservableProperty and, where QUDT "
        "has an equivalent, is linked to its QUDT quantity kind.", lang="en")))
    used = {}
    for v in sorted(g.subjects(RDF.type, EG.Variable)):
        for t in g.objects(v, RDF.type):
            name = _local(t)
            if str(t).startswith(str(EG)) and name.endswith("Measurement") and name != "Measurement" and "Group" not in name:
                used[name[: -len("Measurement")]] = t
    for short in sorted(used):
        prop = PROP[short]
        _typed(g, prop, SOSA.ObservableProperty, SKOS.Concept, OWL.NamedIndividual)
        g.add((prop, SKOS.prefLabel, Literal(_label(short), lang="en")))
        if short in definitions:
            text = definitions[short]
            g.add((prop, SKOS.definition, Literal(text[0].upper() + text[1:], lang="en")))
        g.add((prop, SKOS.inScheme, scheme))
        g.add((scheme, SKOS.hasTopConcept, prop))
        for qk in QUANTITY_KINDS.get(short, []):
            g.add((prop, QUDT.hasQuantityKind, QK[qk]))
            stats["quantity_kind_links"] += 1
        stats["observable_properties"] += 1
    return used


def link_variables(g, stats, used):
    """A measured variable is a sosa:Sensor observing its property; other kinds of signal are only related to it."""
    for v in sorted(g.subjects(RDF.type, EG.Variable)):
        kind = next((str(o) for o in g.objects(v, EG.variableKind)), "measured")
        for short in sorted(s for s, cls in used.items() if (v, RDF.type, cls) in g):
            prop = PROP[short]
            if kind in ("measured", "") and short not in NOT_SENSORS:
                g.add((v, RDF.type, SOSA.Sensor))
                g.add((v, SOSA.observes, prop))
                stats["variables_sensor"] += 1
            else:
                g.add((v, EG.relatesToProperty, prop))
                stats["variables_related_to_property"] += 1
    g.add((EG.relatesToProperty, RDF.type, OWL.ObjectProperty))
    g.add((EG.relatesToProperty, RDFS.label, Literal("relates to property", lang="en")))
    g.add((EG.relatesToProperty, RDFS.comment, Literal(
        "Links a variable that is not a physical sensor (a state, a calculated value, a setpoint or a command) to the observable "
        "property it concerns. Sensors use sosa:observes instead.", lang="en")))


def deprecate_measurement_classes(g, stats, used):
    """The measurement classes stay (so labels and queries keep working) but are deprecated, and stop claiming to be readings."""
    for parent in list(g.objects(EG.Measurement, RDFS.subClassOf)):
        s = str(parent)
        if s.startswith("http://www.w3.org/ns/sosa/") or "saref.etsi.org" in s:
            g.remove((EG.Measurement, RDFS.subClassOf, parent))
            stats["measurement_parents_removed"] += 1
    classes = [EG.Measurement] + [cls for short, cls in sorted(used.items())]
    for cls in classes:
        g.add((cls, OWL.deprecated, Literal(True)))
    for short, cls in sorted(used.items()):
        g.add((cls, DCTERMS.isReplacedBy, PROP[short]))
    g.add((EG.Measurement, DCTERMS.isReplacedBy, EG.MeasurementTypeScheme))
    stats["classes_deprecated"] = len(classes)


# ------------------------------------------------------------------------------------------------------- 2
def equipment_platforms(g, stats):
    """The equipment a variable belongs to (its subsystem) is a sosa:Platform that hosts it."""
    made = set()
    for v in sorted(g.subjects(RDF.type, EG.Variable)):
        ns = _ns(v)
        for sub in g.objects(v, EG.subsystem):
            if ns is None or not str(sub).strip():
                continue
            platform = ns["Platform_" + _slug(sub)]
            if platform not in made:
                _typed(g, platform, SOSA.Platform, OWL.NamedIndividual)
                g.add((platform, RDFS.label, Literal(str(sub).strip(), lang="en")))
                made.add(platform)
            g.add((v, SOSA.isHostedBy, platform))
            stats["variables_hosted"] += 1
    stats["platforms"] = len(made)


# ---------------------------------------------------------------------------------------------------- 3, 4, 7
def _period(text):
    """(start literal, end literal or None) from a free-text coverage, or None."""
    t = str(text)
    ongoing = bool(re.search(r"ongoing", t, re.I))
    dates = [f"{y}-{m}-{d}" for y, m, d in DATE_ISO.findall(t)] + [f"{y}-{m}-{d}" for d, m, y in DATE_EU.findall(t)]
    if dates:
        start = Literal(dates[0], datatype=XSD.date)
        end = None if (ongoing or len(dates) < 2) else Literal(dates[1], datatype=XSD.date)
        return start, end
    years = YEAR.findall(t)
    if years:
        return Literal(years[0], datatype=XSD.gYear), (None if ongoing or len(years) < 2 else Literal(years[1], datatype=XSD.gYear))
    return None


def _duration(text):
    t = str(text).strip()
    if re.match(r"^hourly\b", t, re.I):
        return "PT1H"
    m = DURATION.match(t)
    if not m:
        return None
    n = m.group(1).rstrip("0").rstrip(".") if "." in m.group(1) else m.group(1)
    unit = m.group(2).lower()[0]
    return f"PT{n}{'S' if unit == 's' else 'H' if unit == 'h' else 'M'}"


def dataset_dcat(g, stats):
    service = EG.DataLakeService
    for pilot, ds in sorted(g.subject_objects(MP.hasDataset)):
        ns = _ns(ds)
        if ns is None:
            continue
        stem = _local(ds)
        _typed(g, pilot, FOAF.Organization)
        g.add((ds, DCTERMS.publisher, pilot))
        contact = ns["Contact_" + stem[len("Dataset_"):]]
        _typed(g, contact, VCARD.Organization, OWL.NamedIndividual)
        g.add((contact, VCARD.fn, Literal(str(next(g.objects(pilot, RDFS.label), _local(pilot))))))
        g.add((ds, DCAT.contactPoint, contact))
        cov = next((str(o) for o in g.objects(ds, EG.temporalCoverage)), None)
        period = _period(cov) if cov else None
        if period:
            node = ns["Period_" + stem[len("Dataset_"):]]
            _typed(g, node, DCTERMS.PeriodOfTime, OWL.NamedIndividual)
            g.add((node, DCAT.startDate, period[0]))
            if period[1] is not None:
                g.add((node, DCAT.endDate, period[1]))
            g.add((node, RDFS.label, Literal(cov, lang="en")))
            g.add((ds, DCTERMS.temporal, node))
            stats["datasets_with_period"] += 1
        res = next((str(o) for o in g.objects(ds, EG.timeResolution)), None)
        dur = _duration(res) if res else None
        if dur:
            g.add((ds, DCAT.temporalResolution, Literal(dur, datatype=XSD.duration)))
            stats["datasets_with_resolution"] += 1
        upd = next((str(o) for o in g.objects(ds, EG.updateFrequency)), None)
        for rx, code in EU_FREQUENCY:
            if upd and rx.search(upd):
                g.add((ds, DCTERMS.accrualPeriodicity, FREQ[code]))
                stats["datasets_with_frequency"] += 1
                break
        lic = next((str(o) for o in g.objects(ds, EG.licence)), None)
        if lic:
            if re.search(r"CC BY 4\.0", lic):
                g.add((ds, DCTERMS.license, URIRef("https://creativecommons.org/licenses/by/4.0/")))
            else:
                doc = ns["Licence_" + stem[len("Dataset_"):]]
                _typed(g, doc, DCTERMS.LicenseDocument, OWL.NamedIndividual)
                g.add((doc, RDFS.label, Literal(lic, lang="en")))
                g.add((ds, DCTERMS.license, doc))
            if lic.lower().startswith("restricted"):
                g.add((ds, DCTERMS.accessRights, ACCESS.RESTRICTED))
            stats["datasets_with_licence"] += 1
        loc = next((str(o) for o in g.objects(ds, EG.location)), None)
        if loc:
            place = ns["Place_" + stem[len("Dataset_"):]]
            _typed(g, place, DCTERMS.Location, OWL.NamedIndividual)
            g.add((place, RDFS.label, Literal(loc, lang="en")))
            m = re.search(r"([\d.]+)\s*°?\s*N,\s*([\d.]+)\s*°?\s*E", loc)
            if m:
                g.add((place, WGS.lat, Literal(m.group(1), datatype=XSD.decimal)))
                g.add((place, WGS.long, Literal(m.group(2), datatype=XSD.decimal)))
            g.add((ds, DCTERMS.spatial, place))
        # 4. the lake table is a distribution served by the data lake service
        db = next((str(o) for o in g.objects(ds, EG.storedInDatabase)), None)
        if db:
            dist = ns["Distribution_" + stem[len("Dataset_"):]]
            tables = sorted(str(o) for o in g.objects(ds, EG.storedInDatabaseTable))
            _typed(g, dist, DCAT.Distribution, OWL.NamedIndividual)
            g.add((dist, DCTERMS.title, Literal(f"Data lake: {db} {', '.join(tables)}".strip(), lang="en")))
            for lay in g.objects(ds, EG.tableLayout):
                g.add((dist, EG.tableLayout, lay))
            g.add((dist, DCAT.accessService, service))
            g.add((ds, DCAT.distribution, dist))
            g.add((service, DCAT.servesDataset, ds))
            stats["distributions"] += 1
    if (service, RDF.type, DCAT.DataService) in g:
        g.add((service, DCTERMS.title, Literal("EnergyGuard data lake", lang="en")))
        g.add((service, DCTERMS.description, Literal(
            "PostgreSQL data lake operated by CARTIF, one database per pilot. The host address is not published.", lang="en")))


RDN_PUBLISHERS = (("/rdn/faults#", "RDNFaults"), ("/rdn/timeseries#", "RDNTimeSeries"), ("/rdn#", "RDN"))


def datasets_outside_the_tree(g, stats):
    """Example datasets that RDN's original ontologies define (not listed in the delivery overview): give them their
    sub-pilot as publisher and a title, so every dcat:Dataset satisfies the metadata rules."""
    for ds in sorted(set(g.subjects(RDF.type, DCAT.Dataset))):
        if (ds, DCTERMS.publisher, None) in g:
            continue
        for marker, name in RDN_PUBLISHERS:
            if marker in str(ds):
                pilot = MP[name]
                _typed(g, pilot, FOAF.Organization)
                g.add((ds, DCTERMS.publisher, pilot))
                stats["datasets_outside_tree"] += 1
                break
        if (ds, DCTERMS.title, None) not in g:
            fname = next((str(o) for o in g.objects(ds, URIRef(BASE + "/rdn/timeseries#filename"))), None)
            title = re.sub(r"\.[A-Za-z0-9]+$", "", fname).replace("_", " ") if fname else _local(ds).replace("_", " ")
            g.add((ds, DCTERMS.title, Literal(title, lang="en")))


def geosparql_datasets(g, stats):
    """Datasets with a geometry column are feature collections and state their coordinate reference system."""
    for ds in sorted(set(g.objects(None, MP.hasDataset))):
        variables = list(g.objects(ds, EG.hasVariable))
        if not any(str(o) == "geometry" for v in variables for o in g.objects(v, EG.dataType)):
            continue
        g.add((ds, RDF.type, GEOSPARQL.FeatureCollection))
        stats["geospatial_datasets"] += 1
        for v in variables:
            for text in list(g.objects(v, EG.valueFormat)) + list(g.objects(v, EG.unit)):
                m = re.search(r"EPSG:?\s*(\d{4,5})", str(text))
                if m:
                    g.add((ds, DCTERMS.conformsTo, URIRef(EPSG + m.group(1))))
                    stats["datasets_with_crs"] += 1
                    break


# ------------------------------------------------------------------------------------------------------- 5
def provenance_and_quality(g, stats, sensor_map):
    team = EG.OntologyMaintainers
    _typed(g, team, PROV.Agent, OWL.NamedIndividual)
    g.add((team, RDFS.label, Literal("EnergyGuard ontology maintainers", lang="en")))
    for cls, label, comment, parent in (
            (EG.LakeLink, "Lake link", "The link between a variable and its sensor in the data lake, with where it came from.", PROV.Entity),):
        _typed(g, cls, OWL.Class)
        g.add((cls, RDFS.subClassOf, parent))
        g.add((cls, RDFS.label, Literal(label, lang="en")))
        g.add((cls, RDFS.comment, Literal(comment, lang="en")))
    for p, label in ((EG.hasLakeLink, "has lake link"),):
        _typed(g, p, OWL.ObjectProperty)
        g.add((p, RDFS.label, Literal(label, lang="en")))
    for ds, v in sorted(g.subject_objects(EG.hasVariable)):
        match = next((str(o) for o in g.objects(v, EG.dataLakeMatch)), "")
        ns = _ns(v)
        if match not in ("inferred", "manual") or ns is None:
            continue
        row = sensor_map.get((_local(ds), _local(v)), {})
        link, act = ns["LakeLink_" + _local(v)], ns["LakeMatch_" + _local(v)]
        _typed(g, link, EG.LakeLink, PROV.Entity, OWL.NamedIndividual)
        _typed(g, act, PROV.Activity, OWL.NamedIndividual)
        g.add((act, RDFS.label, Literal("Matched to the data lake from the readings" if match == "inferred"
                                         else "Matched to the data lake and confirmed by a person", lang="en")))
        g.add((act, PROV.wasAssociatedWith, team))
        g.add((link, PROV.wasGeneratedBy, act))
        g.add((link, PROV.wasAttributedTo, team))
        for sid in g.objects(v, EG.dataLakeSensorId):
            g.add((link, EG.dataLakeSensorId, sid))
        g.add((link, EG.matchStatus, Literal("to be confirmed by the pilot" if match == "inferred" else "confirmed")))
        if row.get("note"):
            g.add((link, EG.matchEvidence, Literal(row["note"], lang="en")))
        g.add((v, EG.hasLakeLink, link))
        stats["lake_links_with_provenance"] += 1
    # DQV: a valid range written in another unit than the variable's
    metric = EG.RangeUnitConsistency
    dim = EG.ConsistencyDimension
    _typed(g, dim, DQV.Dimension, OWL.NamedIndividual)
    g.add((dim, RDFS.label, Literal("Consistency", lang="en")))
    _typed(g, metric, DQV.Metric, OWL.NamedIndividual)
    g.add((metric, DQV.inDimension, dim))
    g.add((metric, DQV.expectedDataType, XSD.boolean))
    g.add((metric, SKOS.definition, Literal("True when the valid range is written in the same unit as the variable.", lang="en")))
    for v in sorted(g.subjects(RDF.type, EG.Variable)):
        unit = next((str(o) for o in g.objects(v, EG.unit)), None)
        rng = next((str(o) for o in g.objects(v, EG.validRange)), None)
        ns = _ns(v)
        if not (unit and rng and ns):
            continue
        m = RANGE_UNIT.search(rng)
        if m and m.group(1).strip().lower() != unit.strip().lower():
            node = ns["Quality_RangeUnit_" + _local(v)]
            _typed(g, node, DQV.QualityMeasurement, OWL.NamedIndividual)
            g.add((node, DQV.isMeasurementOf, metric))
            g.add((node, DQV.computedOn, v))
            g.add((node, DQV.value, Literal(False)))
            g.add((node, RDFS.comment, Literal(f"The valid range '{rng}' is written in {m.group(1)}, the variable is in {unit}.", lang="en")))
            g.add((v, DQV.hasQualityMeasurement, node))
            stats["range_unit_inconsistencies"] += 1


# ------------------------------------------------------------------------------------------------------ 10
def ontology_header(g, stats):
    o = ONTOLOGY_IRI
    g.add((o, RDF.type, OWL.Ontology))
    g.add((o, OWL.versionInfo, Literal(ONTOLOGY_VERSION)))
    g.add((o, OWL.versionIRI, URIRef(f"{o}/{ONTOLOGY_VERSION}")))
    g.add((o, DCTERMS.title, Literal("EnergyGuard Ontology (all pilots)", lang="en")))
    g.add((o, DCTERMS.description, Literal(
        "Catalogue of the datasets and variables delivered by the seven EnergyGuard pilots, with the measurement vocabulary and the "
        "location of each series in the EnergyGuard data lake. It describes the data; it does not contain measurements.", lang="en")))
    g.add((o, DCTERMS.license, LICENCE_IRI))


def add_standards_layer(g, stats, definitions, sensor_map):
    bind_prefixes(g)
    used = observable_properties(g, stats, definitions)
    link_variables(g, stats, used)
    deprecate_measurement_classes(g, stats, used)
    equipment_platforms(g, stats)
    service = EG.DataLakeService
    _typed(g, service, DCAT.DataService, OWL.NamedIndividual)
    dataset_dcat(g, stats)
    datasets_outside_the_tree(g, stats)
    geosparql_datasets(g, stats)
    provenance_and_quality(g, stats, sensor_map)
    ontology_header(g, stats)
