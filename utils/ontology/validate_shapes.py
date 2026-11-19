#!/usr/bin/env python3
"""Check ontology/all_pilots.owl against ontology/shapes.ttl (SHACL).

Violation = the file breaks a rule of the metadata template; Warning = fix with the pilot; Info = known gap.
Exit code 1 only when there is a Violation.   Usage: python3 utils/ontology/validate_shapes.py [--show N]
Needs: pip install pyshacl
"""
import argparse
import collections
import sys
from pathlib import Path

import rdflib
from pyshacl import validate

ROOT = Path(__file__).resolve().parents[2]
SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--owl", type=Path, default=ROOT / "ontology" / "all_pilots.owl")
    ap.add_argument("--shapes", type=Path, default=ROOT / "ontology" / "shapes.ttl")
    ap.add_argument("--show", type=int, default=3, help="examples to print per message")
    a = ap.parse_args()
    data = rdflib.Graph(); data.parse(a.owl, format="xml")
    shapes = rdflib.Graph(); shapes.parse(a.shapes, format="turtle")
    conforms, report, _ = validate(data, shacl_graph=shapes, inference="none", advanced=True, allow_warnings=True)
    sev = collections.Counter(); msgs = collections.defaultdict(list)
    for r in report.subjects(rdflib.RDF.type, SH.ValidationResult):
        s = str(report.value(r, SH.resultSeverity)).rsplit("#", 1)[-1]
        sev[s] += 1
        msgs[(s, str(report.value(r, SH.resultMessage)))].append(str(report.value(r, SH.focusNode)).rsplit("#", 1)[-1])
    print(f"{a.owl.name}: {len(data)} triples, {len(shapes)} shape triples")
    print("results:", dict(sev) or "none")
    for (s, m), nodes in sorted(msgs.items(), key=lambda x: (x[0][0] != "Violation", x[0][0] != "Warning", -len(x[1]))):
        print(f"  [{s}] {len(nodes):4}  {m}  e.g. {', '.join(nodes[: a.show])}")
    return 1 if sev["Violation"] else 0


if __name__ == "__main__":
    sys.exit(main())
