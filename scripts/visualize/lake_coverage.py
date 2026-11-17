#!/usr/bin/env python3
"""How much of each pilot's metadata is found in the data lake.

    neo4j-venv/bin/python scripts/visualize/lake_coverage.py           # terminal table
    neo4j-venv/bin/python scripts/visualize/lake_coverage.py --html    # + output/visualizations/lake_coverage.html

Per pilot: datasets with a data-lake location, and variables by how they were found
(exact, normalised, pattern, column, timestamp) or not found (none).
"""
from collections import defaultdict
from html import escape

from _common import (PILOT_COLORS, GREY, bar, bold, dim, output_path, parser, pilot_key, run)

QUERY = """
MATCH (p:Pilot)-[:mp__hasDataset]->(d:Dataset)
OPTIONAL MATCH (d)-[:eg__hasVariable]->(v)
WITH p, d, collect(DISTINCT v) AS vs
RETURN p.displayName AS pilot, d.displayName AS dataset, d.eg__storedInDatabase IS NOT NULL AS located,
       [v IN vs | coalesce(v.lakeMatch, 'none')] AS matches, [v IN vs | v.uri] AS uris
"""
KINDS = ["exact", "normalised", "inferred", "manual", "pattern", "column", "timestamp", "none"]
KIND_COLORS = {"exact": "#2E7D32", "normalised": "#66BB6A", "inferred": "#FFD54F", "manual": "#FFB300", "pattern": "#9CCC65", "column": "#26A69A",
               "timestamp": "#B0BEC5", "none": "#E57373"}


def collect(a):
    stats = defaultdict(lambda: {"datasets": 0, "located": 0, "vars": {}})
    for r in run(a, QUERY):
        s = stats[pilot_key(r["pilot"])]
        s["datasets"] += 1
        s["located"] += 1 if r["located"] else 0
        for uri, m in zip(r["uris"], r["matches"]):
            if uri not in s["vars"] or s["vars"][uri] == "none":   # BER: one variable in two datasets
                s["vars"][uri] = m
    return stats


def main():
    p = parser("Data lake coverage per pilot")
    p.add_argument("--html", action="store_true", help="also write output/visualizations/lake_coverage.html")
    a = p.parse_args()
    stats = collect(a)

    print(bold(f"{'pilot':9}{'datasets in lake':>18}   {'variables found in lake':<34}" +
               "".join(f"{k:>11}" for k in KINDS)))
    for pilot in sorted(stats):
        s = stats[pilot]
        counts = defaultdict(int)
        for m in s["vars"].values():
            counts[m] += 1
        n = len(s["vars"])
        found = n - counts["none"]
        frac = found / n if n else 0
        print(f"{pilot:9}{s['located']:>9}/{s['datasets']:<8}   {bar(frac)} {found:>4}/{n:<5} {frac:>4.0%}  " +
              "".join((f"{counts[k]:>11}" if counts[k] else dim(f"{'·':>11}")) for k in KINDS))

    if a.html:
        rows = []
        for pilot in sorted(stats):
            s = stats[pilot]
            counts = defaultdict(int)
            for m in s["vars"].values():
                counts[m] += 1
            n = max(len(s["vars"]), 1)
            segs = "".join(f'<div class="seg" title="{k}: {counts[k]}" style="width:{100 * counts[k] / n:.2f}%;'
                           f'background:{KIND_COLORS[k]}">{counts[k] if counts[k] * 100 / n > 6 else ""}</div>'
                           for k in KINDS if counts[k])
            rows.append(f'<tr><td class="p" style="border-left:6px solid {PILOT_COLORS.get(pilot, GREY)}">{escape(pilot)}</td>'
                        f'<td>{s["located"]} / {s["datasets"]}</td><td>{len(s["vars"])}</td>'
                        f'<td class="barcell"><div class="bar">{segs or "<i>no variables yet</i>"}</div></td></tr>')
        legend = "".join(f'<span><i style="background:{c}"></i>{k}</span>' for k, c in KIND_COLORS.items())
        html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Data lake coverage</title>
<style>
 body{{font-family:system-ui,sans-serif;margin:32px;color:#263238}} h1{{font-weight:600}}
 table{{border-collapse:collapse;width:100%;max-width:1100px}} td,th{{padding:10px 12px;text-align:left;border-bottom:1px solid #ECEFF1}}
 td.p{{font-weight:600}} .barcell{{width:60%}} .bar{{display:flex;height:26px;border-radius:4px;overflow:hidden;background:#F5F5F5}}
 .seg{{color:#fff;font-size:12px;display:flex;align-items:center;justify-content:center}}
 .legend span{{margin-right:18px;font-size:14px}} .legend i{{display:inline-block;width:12px;height:12px;margin-right:6px;border-radius:2px}}
</style></head><body>
<h1>EnergyGuard · pilot metadata found in the data lake</h1>
<p class="legend">{legend}</p>
<table><tr><th>pilot</th><th>datasets located</th><th>variables</th><th>how the variables were found</th></tr>
{''.join(rows)}</table>
<p style="color:#78909C;margin-top:24px">exact / normalised: the variable's sensor in the lake ·
pattern: one sensor per device · column: a column of a wide table · none: not found in the lake</p>
</body></html>"""
        path = output_path("lake_coverage.html")
        path.write_text(html, encoding="utf-8")
        print(f"\n-> {path.relative_to(path.parents[1])}")


if __name__ == "__main__":
    main()
