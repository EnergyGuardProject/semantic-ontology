"""Explore the EnergyGuard ontology from Python, without knowing Cypher.

    import eg                                  # what you give it                -> what you get
    eg.pilots()                                #                                 -> pilots with dataset / variable counts
    eg.datasets(text=None, pilot=None)         # optional word, pilot            -> datasets
    eg.measurement_types(pilot=None)           # optional pilot                  -> measurement types, described, with counts
    eg.variables(measurement_type=None, pilot=None)  # optional type, pilot     -> variables
    eg.find(text, pilot=None, limit=50)        # a word, optional pilot          -> matching variables
    eg.variable(name)                          # a variable name                 -> where it lives (dataset, data lake sensor id)
    eg.describe(name)                          # a variable name                 -> PRINTS a card of everything known
    eg.tree(pilot, per_dataset=4)              # a pilot                         -> PRINTS pilot > datasets > variables
    eg.subsystems()                            #                                 -> subsystems with counts
    eg.readings_sql(name, n=10)                # a variable name                 -> the SQL text for its readings
    eg.connect(uri, user, password)            # (optional, see below)           -> connects to Neo4j

Connection: put NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD in a file called .env next to this file (see .env.example),
or set them as environment variables, or call eg.connect(uri, user, password).
Every function returns a list of dicts (wrap in pandas.DataFrame to see a table).
"""
import os
from pathlib import Path

from neo4j import GraphDatabase

_driver = None


def _load_dotenv():
    """Read NEO4J_* settings from a file called .env next to this file, if there is one (real environment variables win)."""
    f = Path(__file__).resolve().parent / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            key, sep, val = line.partition("=")
            if sep and key.strip().startswith("NEO4J_"):
                os.environ.setdefault(key.strip(), val.strip().strip("'\""))


def connect(uri=None, user=None, password=None):
    """Connect to the ontology's Neo4j. Arguments default to the environment variables
    NEO4J_URI (default bolt://localhost:7687), NEO4J_USER (default neo4j) and NEO4J_PASSWORD.
    Called automatically on first use; call it yourself to point at a different server."""
    global _driver
    _load_dotenv()
    uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = user or os.environ.get("NEO4J_USER", "neo4j")
    password = password or os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise RuntimeError("No Neo4j password: set NEO4J_PASSWORD or call eg.connect(uri, user, password).")
    if _driver is not None:
        _driver.close()
    _driver = GraphDatabase.driver(uri, auth=(user, password))
    _driver.verify_connectivity()
    return _driver


def _q(cypher, **params):
    # n10s stores most values as lists (hence the [0]) and prefixes names (eg__, mp__); only this file needs to know.
    if _driver is None:
        connect()
    records, _, _ = _driver.execute_query(cypher, params, routing_="r")
    return [r.data() for r in records]


def pilots():
    """Which pilots exist, with how many datasets and variables?"""
    return _q("""
MATCH (p:Pilot)-[:mp__hasDataset]->(d:Dataset)
OPTIONAL MATCH (d)-[:eg__hasVariable]->(v)
RETURN p.displayName AS pilot, count(DISTINCT d) AS datasets, count(DISTINCT v) AS variables
ORDER BY variables DESC""")


def datasets(text=None, pilot=None):
    """Datasets whose title or description mentions a word, e.g. 'building'. No word: all datasets."""
    return _q("""
MATCH (p:Pilot)-[:mp__hasDataset]->(d:Dataset)
WHERE ($pilot IS NULL OR p.displayName STARTS WITH $pilot)
  AND ($text IS NULL OR toLower(d.displayName) CONTAINS toLower($text)
       OR any(x IN coalesce(d.dcterms__description, []) WHERE toLower(x) CONTAINS toLower($text)))
RETURN p.displayName AS pilot, d.displayName AS dataset,
       coalesce(d.eg__storedInDatabase[0], 'not in the lake') AS database
ORDER BY pilot""", text=text, pilot=pilot)


def measurement_types(pilot=None):
    """Every measurement type (Temperature, Pressure, ... the `measurement_type` for variables()) with a short
    description and its number of variables; optionally only one pilot's."""
    return _q("""
MATCH (p:Pilot)-[:mp__hasDataset]->(:Dataset)-[:eg__hasVariable]->(v)-[:INSTANCE_OF]->(c)
WHERE c.localName ENDS WITH 'Measurement' AND ($pilot IS NULL OR p.displayName STARTS WITH $pilot)
RETURN replace(c.localName, 'Measurement', '') AS measurement_type,
       replace(coalesce(c.rdfs__comment[0], ''), 'Measurement type: ', '') AS description,
       count(DISTINCT v) AS variables
ORDER BY variables DESC""", pilot=pilot)


def subsystems():
    """Every subsystem (the equipment or part of the installation a variable belongs to: dryer, Battery, Heat pump, ...) with its variable count."""
    return _q("""
MATCH (:Dataset)-[:eg__hasVariable]->(v)
WHERE v.eg__subsystem IS NOT NULL
RETURN v.eg__subsystem[0] AS subsystem, count(DISTINCT v) AS variables
ORDER BY variables DESC""")


def variables(measurement_type=None, pilot=None):
    """Variables (each a sensor or a column of a dataset), optionally of one measurement type (Temperature, Pressure, ...) and/or one pilot.
    No arguments: every variable, including those without a measurement type."""
    return _q("""
MATCH (p:Pilot)-[:mp__hasDataset]->(d:Dataset)-[:eg__hasVariable]->(v)
WHERE $pilot IS NULL OR p.displayName STARTS WITH $pilot
OPTIONAL MATCH (v)-[:INSTANCE_OF]->(c) WHERE c.localName ENDS WITH 'Measurement'
WITH p, d, v, c WHERE $mtype IS NULL OR c.localName = $mtype + 'Measurement'
RETURN DISTINCT p.displayName AS pilot, d.displayName AS dataset, v.displayName AS variable,
       replace(coalesce(c.localName, ''), 'Measurement', '') AS measurement_type, v.eg__unit[0] AS unit
ORDER BY pilot, dataset, variable""", mtype=measurement_type, pilot=pilot)


def variable(name):
    """What is this variable, and what is its id in the data lake? One row per dataset that contains it."""
    return _q("""
MATCH (p:Pilot)-[:mp__hasDataset]->(d:Dataset)-[:eg__hasVariable]->(v {displayName: $name})
RETURN p.displayName AS pilot, d.displayName AS dataset, v.dcterms__description[0] AS meaning,
       v.eg__unit[0] AS unit, v.lakeSensorId AS data_lake_sensor_id""", name=name)


sensor = variable   # old name, kept so existing notebooks keep working


def readings_sql(name, n=10):
    """The SQL that fetches the latest readings of a variable from its pilot's data lake database."""
    ids = {r["data_lake_sensor_id"] for r in variable(name) if r["data_lake_sensor_id"]}
    if not ids:
        return f"-- '{name}' has no data lake sensor id"
    lake_id = ids.pop()
    return (f"SELECT c.datetime, f.f_value\n"
            f"FROM public.f_tsdata f JOIN public.d_calendar c USING (calendar_id)\n"
            f"WHERE f.sensor_id = '{lake_id}'\n"
            f"ORDER BY f.calendar_id DESC LIMIT {n};")


def find(text, pilot=None, limit=50):
    """Search variables by a word in their name, description or data lake sensor id, e.g. 'storage tank' or 'pressure'."""
    return _q("""
MATCH (p:Pilot)-[:mp__hasDataset]->(d:Dataset)-[:eg__hasVariable]->(v)
WHERE ($pilot IS NULL OR p.displayName STARTS WITH $pilot)
  AND (toLower(v.displayName) CONTAINS toLower($t)
       OR toLower(coalesce(v.lakeSensorId, '')) CONTAINS toLower($t)
       OR any(x IN coalesce(v.dcterms__description, []) WHERE toLower(x) CONTAINS toLower($t)))
RETURN p.displayName AS pilot, d.displayName AS dataset, v.displayName AS variable,
       v.dcterms__description[0] AS meaning, v.eg__unit[0] AS unit,
       replace(coalesce(v.measurementType, ''), 'Measurement', '') AS measurement_type
ORDER BY pilot, dataset, variable LIMIT $limit""", t=text, pilot=pilot, limit=limit)


_CARD = [("meaning", "Meaning"), ("measurement_type", "Measurement type"), ("unit", "Unit"), ("range", "Valid range"),
         ("kind", "Kind"), ("dtype", "Data type"), ("sampling", "Sampling"), ("aggregation", "Aggregation"),
         ("subsystem", "Subsystem"), ("data_lake_sensor_id", "Data lake sensor id"), ("data_lake_match", "Data lake match"),
         ("database", "Database"), ("table", "Table")]


def describe(name):
    """Print everything the ontology knows about one variable (one card per dataset that contains it)."""
    rows = _q("""
MATCH (p:Pilot)-[:mp__hasDataset]->(d:Dataset)-[:eg__hasVariable]->(v {displayName: $name})
RETURN p.displayName AS pilot, d.displayName AS dataset, d.eg__location[0] AS location,
       d.eg__temporalCoverage[0] AS period, d.eg__updateFrequency[0] AS updates,
       v.dcterms__description[0] AS meaning,
       replace(coalesce(v.measurementType, ''), 'Measurement', '') AS measurement_type, v.eg__unit[0] AS unit,
       coalesce(v.eg__minValue[0], '?') + ' to ' + coalesce(v.eg__maxValue[0], '?') AS range,
       v.eg__variableKind[0] AS kind, v.eg__dataType[0] AS dtype, v.eg__sampling[0] AS sampling,
       v.eg__aggregation[0] AS aggregation, v.eg__subsystem[0] AS subsystem,
       v.lakeSensorId AS data_lake_sensor_id, v.eg__dataLakeMatch[0] AS data_lake_match,
       d.eg__storedInDatabase[0] AS database, d.eg__storedInDatabaseTable[0] AS table""", name=name)
    if not rows:
        print(f"No variable called '{name}'. Try eg.find('{name}') or eg.variables().")
    for r in rows:
        print(f"== {name}  ({r['pilot']}, dataset: {r['dataset']})")
        print(f"   Location {r['location'] or '-'} | period {r['period'] or '-'} | updated {r['updates'] or '-'}")
        for key, label in _CARD:
            print(f"   {label:<15} {r[key] if r[key] not in (None, '') else '-'}")


def tree(pilot, per_dataset=4):
    """Print one pilot as a tree: pilot -> datasets -> first variables of each."""
    rows = _q("""
MATCH (p:Pilot)-[:mp__hasDataset]->(d:Dataset)
WHERE p.displayName STARTS WITH $pilot
OPTIONAL MATCH (d)-[:eg__hasVariable]->(v)
WITH p, d, collect(DISTINCT v.displayName) AS vs
RETURN p.displayName AS pilot, d.displayName AS dataset, vs ORDER BY dataset""", pilot=pilot)
    if not rows:
        print(f"No pilot called '{pilot}'. Try eg.pilots().")
        return
    print(rows[0]["pilot"])
    for i, r in enumerate(rows):
        last = i == len(rows) - 1
        print(f"{'└──' if last else '├──'} {r['dataset']}  ({len(r['vs'])} variables)")
        pad = "    " if last else "│   "
        for v in sorted(r["vs"])[:per_dataset]:
            print(f"{pad}• {v}")
        if len(r["vs"]) > per_dataset:
            print(f"{pad}• ... and {len(r['vs']) - per_dataset} more")
