#!/usr/bin/env python3
"""How to use the graph: everyday questions, the Cypher query that answers each, and the answer.

    neo4j-venv/bin/python scripts/visualize/query_demo.py                       # all questions
    neo4j-venv/bin/python scripts/visualize/query_demo.py --question 3          # just one
    neo4j-venv/bin/python scripts/visualize/query_demo.py --sensor PT-U301 --measurement-type Pressure --topic heating

Every query shown can be pasted as-is into the Neo4j Browser (replace $parameters by values, or set them
with  :param sensor => 'TT-D101').
"""
import textwrap

from _common import bold, cyan, dim, first, parser, run

QUESTIONS = [
    ("What is in the ontology?",
     "Count datasets and variables per pilot.",
     """
MATCH (p:Pilot)-[:mp__hasDataset]->(d:Dataset)
OPTIONAL MATCH (d)-[:eg__hasVariable]->(v)
RETURN p.displayName AS pilot, count(DISTINCT d) AS datasets, count(DISTINCT v) AS variables
ORDER BY variables DESC""", {}),

    ("Which pilots measure {measurement_type}, and with how many sensors?",
     "Every variable has a shared measurement class, so one label finds the same measurement type in all pilots.",
     """
MATCH (p:Pilot)-[:mp__hasDataset]->(:Dataset)-[:eg__hasVariable]->(v)-[:INSTANCE_OF]->(c)
WHERE c.localName = $measurement_type + 'Measurement'
RETURN p.displayName AS pilot, count(DISTINCT v) AS sensors,
       collect(DISTINCT v.displayName)[0..6] AS examples
ORDER BY sensors DESC""", {"measurement_type": "measurement_type"}),

    ("What is sensor {sensor}, and where are its readings?",
     "Follow variable -> dataset -> data lake; the result includes the SQL to fetch the data.",
     """
MATCH (p:Pilot)-[:mp__hasDataset]->(d:Dataset)-[:eg__hasVariable]->(v)
WHERE v.displayName = $sensor
RETURN p.displayName AS pilot, d.displayName AS dataset,
       v.dcterms__description[0] AS meaning, v.eg__unit[0] AS unit,
       coalesce(v.eg__validRange[0], v.eg__minValue[0] + ' – ' + v.eg__maxValue[0]) AS valid_range,
       d.eg__storedInDatabase[0] AS database, v.lakeSensorId AS lake_sensor_id""", {"sensor": "sensor"}),

    ("Which other sensors are in the same group as {sensor}?",
     "Sensor groups come from the pilot's own ontology (e.g. all temperatures of one subsystem).",
     """
MATCH (v {displayName: $sensor})<-[:eg__hasMeasurement]-(g)-[:eg__hasMeasurement]->(other)
RETURN g.displayName AS grp, count(other) AS sensors_in_group,
       collect(other.displayName)[0..10] AS sensors""", {"sensor": "sensor"}),

    ("Which datasets are about '{topic}'?",
     "Search dataset titles and descriptions.",
     """
MATCH (p:Pilot)-[:mp__hasDataset]->(d:Dataset)
WHERE toLower(d.displayName) CONTAINS toLower($topic)
   OR any(x IN coalesce(d.dcterms__description, []) WHERE toLower(x) CONTAINS toLower($topic))
RETURN p.displayName AS pilot, d.displayName AS dataset, d.eg__temporalCoverage[0] AS period,
       coalesce(d.eg__storedInDatabase[0], 'not in the lake') AS database
ORDER BY pilot""", {"topic": "topic"}),

    ("Which measurement types does each pilot have?",
     "One row per pilot, listing its kinds of measurement.",
     """
MATCH (p:Pilot)-[:mp__hasDataset]->(:Dataset)-[:eg__hasVariable]->(v)-[:INSTANCE_OF]->(c)
WITH p, replace(c.localName, 'Measurement', '') AS mtype, count(DISTINCT v) AS n
ORDER BY n DESC
RETURN p.displayName AS pilot, collect(mtype + ' ' + n) AS measurement_types
ORDER BY pilot""", {}),
]


def table(rows, width=34):
    if not rows:
        print(dim("   (no result)"))
        return
    cols = list(rows[0])
    fmt = lambda v: (", ".join(map(str, v)) if isinstance(v, list) else ("" if v is None else str(v)))
    widths = {c: min(max(len(c), *(len(fmt(r[c])) for r in rows)), width if c != cols[-1] else 90) for c in cols}
    print("   " + "  ".join(bold(c.ljust(widths[c])) for c in cols))
    for r in rows:
        print("   " + "  ".join(fmt(r[c])[:widths[c]].ljust(widths[c]) for c in cols))


def main():
    p = parser("Everyday questions answered with Cypher")
    p.add_argument("--question", type=int, help=f"only question 1..{len(QUESTIONS)}")
    p.add_argument("--sensor", default="TT-D101", help="a variable name (default TT-D101, a BER temperature)")
    p.add_argument("--measurement-type", default="Temperature",
                   help="a measurement type: Temperature, Pressure, Flow, Power, Energy, Current, Voltage, ...")
    p.add_argument("--topic", default="building", help="a word to look for in dataset titles/descriptions")
    a = p.parse_args()
    values = {"sensor": a.sensor, "measurement_type": a.measurement_type, "topic": a.topic}

    for i, (question, how, query, params) in enumerate(QUESTIONS, 1):
        if a.question and a.question != i:
            continue
        q = question.format(**values)
        print(bold(cyan(f"\n{i}. {q}")))
        print(dim("   " + how))
        print(dim(textwrap.indent(query.strip(), "   │ ")))
        if params:
            print(dim("   │ params: " + ", ".join(f"${k} = '{values[v]}'" for k, v in params.items())))
        rows = run(a, query, **{k: values[v] for k, v in params.items()})
        print()
        table(rows)
        if i == 3 and rows and first(rows[0].get("lake_sensor_id")):
            print(dim("\n   readings (run in the pilot's database):"))
            print(f"   SELECT c.datetime, f.f_value FROM public.f_tsdata f JOIN public.d_calendar c USING (calendar_id)\n"
                  f"   WHERE f.sensor_id = '{first(rows[0]['lake_sensor_id'])}' ORDER BY f.calendar_id DESC LIMIT 100;")


if __name__ == "__main__":
    main()
