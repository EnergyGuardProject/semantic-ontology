#!/usr/bin/env python3
"""Assemble the file Neo4j imports from the hand-written parts.

    ontology/core.ttl            the few terms no standard covers
    ontology/catalogue/*.ttl     pilots, datasets, variables (curated by hand)
 -> ontology/all_pilots.owl      RDF/XML, the one file n10s imports (generated, do not edit)

Nothing here reads the partners' Excel files. Usage: python3 utils/ontology/assemble.py
"""
import os
import re
import sys
from pathlib import Path

import rdflib

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ontology" / "all_pilots.owl"
PREFIXES = {"eg": "https://www.energyguard.eu/ontology#", "mp": "https://www.energyguard.eu/ontology/merged-pilots#",
            "prop": "https://www.energyguard.eu/ontology/property#"}


def main():
    g = rdflib.Graph()
    parts = [ROOT / "ontology" / "core.ttl"] + sorted((ROOT / "ontology" / "catalogue").glob("*.ttl"))
    for p in parts:
        g.parse(p, format="turtle")
    final = rdflib.Graph()
    for prefix, ns in list(g.namespaces()) + list(PREFIXES.items()):
        final.bind(prefix, ns, override=True)
    for t in sorted(g, key=lambda t: tuple(f"{type(x).__name__}{x}" for x in t)):
        final.add(t)
    xml = final.serialize(format="pretty-xml", encoding="utf-8").decode("utf-8")
    OUT.write_bytes(xml.encode("utf-8"))
    print(f"{len(parts)} files, {len(g)} triples -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    if os.environ.get("PYTHONHASHSEED") != "0":      # same inputs, byte-identical output
        os.environ["PYTHONHASHSEED"] = "0"
        os.execv(sys.executable, [sys.executable] + sys.argv)
    main()
