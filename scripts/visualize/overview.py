#!/usr/bin/env python3
"""Print the ontology structure as a tree in the terminal.

    neo4j-venv/bin/python scripts/visualize/overview.py                 # pilots -> datasets
    neo4j-venv/bin/python scripts/visualize/overview.py --pilot BER     # ... and that pilot's variables
    neo4j-venv/bin/python scripts/visualize/overview.py --pilot CEA --limit 0   # all variables

Shows for every dataset: number of variables, where it lives in the data lake, and how many of
its variables were found there.
"""
from collections import defaultdict

from _common import (bold, cyan, dim, first, green, parser, pilot_key, red, run, yellow)

DATASETS = """
MATCH (p:Pilot)-[:mp__hasDataset]->(d:Dataset)
OPTIONAL MATCH (d)-[:eg__hasVariable]->(v)
WITH p, d, count(v) AS variables, count(CASE WHEN v.lakeMatch IS NOT NULL AND v.lakeMatch <> 'none' THEN 1 END) AS located
RETURN p.displayName AS pilot, d.displayName AS dataset, variables, located,
       d.eg__storedInDatabase AS db, d.eg__storedInDatabaseTable AS tables, d.eg__tableLayout AS layout
ORDER BY pilot, dataset
"""
SUBPILOTS = "MATCH (p:Pilot)-[:mp__hasSubPilot]->(s) RETURN p.displayName AS pilot, collect(s.displayName) AS subs"
VARIABLES = """
MATCH (p:Pilot)-[:mp__hasDataset]->(d:Dataset)-[:eg__hasVariable]->(v)
WHERE p.displayName STARTS WITH $pilot
RETURN d.displayName AS dataset, v.displayName AS name, v.measurementType AS class,
       coalesce(v.lakeSensorId, v.lakeSensorPattern, v.lakeColumn) AS lake, v.lakeMatch AS how,
       v.eg__unit AS unit
ORDER BY dataset, name
"""


def location(row):
    if not first(row["db"]):
        return red("not in the data lake")
    tables = row["tables"] if isinstance(row["tables"], list) else [row["tables"]]
    t = tables[0] + (f" (+{len(tables) - 1})" if len(tables) > 1 else "")
    return cyan(f"{first(row['db'])}.{t}") + dim(f" [{first(row['layout'])}]")


def main():
    p = parser("Print the ontology structure as a tree")
    p.add_argument("--pilot", help="also list this pilot's variables (e.g. BER, CEA, REA)")
    p.add_argument("--limit", type=int, default=15, help="variables shown per dataset with --pilot (0 = all)")
    a = p.parse_args()

    rows = run(a, DATASETS)
    subs = {r["pilot"]: r["subs"] for r in run(a, SUBPILOTS)}
    by_pilot = defaultdict(list)
    for r in rows:
        by_pilot[r["pilot"]].append(r)
    variables = defaultdict(list)
    if a.pilot:
        for v in run(a, VARIABLES, pilot=a.pilot.upper()):
            variables[v["dataset"]].append(v)

    n_vars = run(a, "MATCH (:Dataset)-[:eg__hasVariable]->(v) RETURN count(DISTINCT v) AS n")[0]["n"]
    print(bold("EnergyGuard ontology") + dim(f"   {len(by_pilot)} pilots · {len(rows)} datasets · {n_vars} variables"))
    pilots = sorted(by_pilot)
    for i, pilot in enumerate(pilots):
        last_p = i == len(pilots) - 1
        ds = by_pilot[pilot]
        nv = sum(r["variables"] for r in ds)
        extra = dim(f"  sub-pilots: {', '.join(sorted(subs[pilot]))}") if subs.get(pilot) else ""
        print(("└─ " if last_p else "├─ ") + bold(pilot_key(pilot)) +
              dim(f"  {len(ds)} dataset{'s' if len(ds) != 1 else ''} · {nv} variables") + extra)
        pad = "   " if last_p else "│  "
        for j, r in enumerate(ds):
            last_d = j == len(ds) - 1
            frac = f"{r['located']}/{r['variables']}" if r["variables"] else "no variables yet"
            colour = green if r["variables"] and r["located"] == r["variables"] else yellow if r["located"] else dim
            print(pad + ("└─ " if last_d else "├─ ") + r["dataset"][:70] +
                  dim("  vars in lake ") + colour(frac) + "  " + location(r))
            if a.pilot and pilot_key(pilot).upper() == a.pilot.upper():
                vs = variables.get(r["dataset"], [])
                shown = vs if a.limit == 0 else vs[:a.limit]
                vpad = pad + ("   " if last_d else "│  ")
                for v in shown:
                    lake = first(v["lake"])
                    how = first(v["how"]) or "none"
                    lake_txt = (green(lake) if how in ("exact", "column", "timestamp") else yellow(lake)) if lake else red("—")
                    print(vpad + "· " + f"{v['name'][:38]:38} " + dim(f"{(v['class'] or '').replace('Measurement', ''):14} ")
                          + dim(f"{(first(v['unit']) or ''):8} ") + lake_txt + dim(f"  ({how})"))
                if len(vs) > len(shown):
                    print(vpad + dim(f"… {len(vs) - len(shown)} more (use --limit 0)"))
    print(dim("\nlegend: vars in lake = variables found in the data lake / variables in the metadata"))


if __name__ == "__main__":
    main()
