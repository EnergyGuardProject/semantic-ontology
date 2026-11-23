#!/usr/bin/env python3
"""Report what a partner's metadata workbook would change in the curated catalogue.

Read-only: nothing is written to ontology/ and nothing is applied. You read the report, then edit
ontology/catalogue/<pilot>.ttl by hand for the differences you accept.

    python3 utils/ontology/workbook_diff.py                    # every workbook in pilot_metadata/
    python3 utils/ontology/workbook_diff.py cea ber            # only some pilots
    python3 utils/ontology/workbook_diff.py --dir ~/new_files --out report.md

Needs: pip install rdflib openpyxl. The workbook readers come from the archived generator
(archive/ontology_generator/build_all_pilots_owl.py), which is only imported, never run.
"""
import argparse
import sys
from pathlib import Path

import rdflib
from rdflib import RDF, RDFS, Namespace
from rdflib.namespace import DCTERMS

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "archive" / "ontology_generator"))
import build_all_pilots_owl as old  # noqa: E402  (readers and normalisers only)

EG = Namespace("https://ontology.energy-guard.eu/core#")
MP = Namespace("https://ontology.energy-guard.eu/pilots#")
QUDT = Namespace("http://qudt.org/vocab/unit/")
SCHEMA = Namespace("http://schema.org/")
QS = Namespace("http://qudt.org/schema/qudt/")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
QUDT_HAS_UNIT = rdflib.URIRef("http://qudt.org/schema/qudt/hasUnit")


def text(g, s, p):
    """One literal, English preferred."""
    vals = sorted(g.objects(s, p), key=lambda o: (getattr(o, "language", None) != "en", str(o)))
    return str(vals[0]) if vals else None


def all_text(g, s, p):
    return {n(str(o)) for o in g.objects(s, p)}


def load_catalogue():
    g = rdflib.Graph()
    for f in [ROOT / "ontology" / "core.ttl", *sorted((ROOT / "ontology" / "catalogue").glob("*.ttl"))]:
        g.parse(f)
    return g


def catalogue_of(g, pilot):
    """{dataset title: {variable label: record}} for one pilot."""
    out = {}
    for ds in g.subjects(DCTERMS.publisher, MP[pilot.upper()]):
        if (ds, RDF.type, DCAT.Dataset) not in g:
            continue
        variables = {}
        for v in g.objects(ds, SCHEMA.variableMeasured):
            unit = g.value(v, QUDT_HAS_UNIT)
            variables[text(g, v, RDFS.label)] = {
                "description": text(g, v, DCTERMS.description),
                "all_descriptions": all_text(g, v, DCTERMS.description),
                "unit_iri": unit,
                "unit": text(g, unit, QS.symbol) if unit else None,
                "range": text(g, v, SKOS.note),
            }
        out[text(g, ds, DCTERMS.title)] = {"description": text(g, ds, DCTERMS.description),
                                           "all_descriptions": all_text(g, ds, DCTERMS.description), "variables": variables}
    return out


def n(s):
    return old.norm(s) if s else ""


def compare(pilot, datasets, cat):
    lines, all_cat_vars = [], {}
    for c in cat.values():
        all_cat_vars.update(c["variables"])
    seen_vars = set()
    for d in datasets:
        title = d["fields"].get("title") or "(no title)"
        match = next((t for t in cat if n(t) == n(title)), None)
        lines.append(f"### {title}")
        if match is None:
            lines.append(f"- NEW dataset: not in the catalogue (catalogue has: {', '.join(sorted(cat)) or 'none'})")
            lines.append(f"- {len(d['variables'])} variables in the workbook")
            continue
        cd = cat[match]
        wd = d["fields"].get("description")
        if wd and n(wd) not in cd["all_descriptions"]:
            lines.append(f"- description differs\n    workbook : {wd}\n    catalogue: {cd['description']}")
        pool = all_cat_vars if d["scope"] == "pilot" else cd["variables"]
        names = set()
        for rec in d["variables"]:
            name = rec["name"]
            names.add(name)
            cv = pool.get(name)
            if cv is None:
                lines.append(f"- NEW variable {name}: {rec.get('description') or ''} [{rec.get('unit') or '-'}]")
                continue
            seen_vars.add(name)
            wdesc = rec.get("description")
            if wdesc and cv["all_descriptions"] and n(wdesc) not in cv["all_descriptions"]:
                lines.append(f"- {name}: description\n    workbook : {wdesc}\n    catalogue: {cv['description']}")
            wu = rec.get("unit")
            same = old.qudt_unit(wu) == cv["unit_iri"] if wu and cv["unit_iri"] and old.qudt_unit(wu) else None
            if wu and cv["unit"] and (same is False or (same is None and n(wu) != n(cv["unit"]))):
                lines.append(f"- {name}: unit workbook '{wu}' vs catalogue '{cv['unit']}'")
            elif wu and not cv["unit"]:
                lines.append(f"- {name}: workbook has unit '{wu}', catalogue has none")
        if d["scope"] != "pilot":
            for gone in sorted(set(cd["variables"]) - names):
                lines.append(f"- variable {gone} is in the catalogue but not in the workbook")
        if len(lines) and lines[-1].startswith("###"):
            lines.append("- no differences")
    if any(d["scope"] == "pilot" for d in datasets):
        for gone in sorted(set(all_cat_vars) - seen_vars):
            lines.append(f"- variable {gone} is in the catalogue but not in the workbook")
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pilots", nargs="*", help="ciemat ber cea cartif rea engreen (default: all)")
    ap.add_argument("--dir", default=str(ROOT / "pilot_metadata"), help="folder with the workbooks")
    ap.add_argument("--out", help="also write the report to this Markdown file")
    a = ap.parse_args()
    g = load_catalogue()
    wanted = {p.lower() for p in a.pilots}
    report = ["# Workbook vs curated catalogue", "", "Nothing here has been applied.", ""]
    for reader, args, ns, pilot_cls, _schema in old.PILOT_SOURCES:
        pilot = str(pilot_cls).rsplit("#", 1)[1]
        if wanted and pilot.lower() not in wanted:
            continue
        path = Path(a.dir) / args[0]
        report.append(f"## {pilot}")
        if not path.exists():
            report += [f"workbook not found: {path}", ""]
            continue
        report += compare(pilot, reader(path, *args[1:]), catalogue_of(g, pilot)) + [""]
    out = "\n".join(report)
    print(out)
    if a.out:
        Path(a.out).write_text(out + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
