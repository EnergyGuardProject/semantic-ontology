#!/usr/bin/env python3
"""Export the ontology structure to GraphML, for Gephi, yEd or Cytoscape.

    neo4j-venv/bin/python scripts/visualize/export_graphml.py                 # all pilots
    neo4j-venv/bin/python scripts/visualize/export_graphml.py --pilot CEA

Writes output/visualizations/structure[_<pilot>].graphml with pilot, dataset, variable and class nodes
(attribute `kind`) and has_dataset / has_variable / instance_of edges.
"""
import networkx as nx

from _common import first, output_path, parser, pilot_key, run

QUERY = """
MATCH (p:Pilot)-[:mp__hasDataset]->(d:Dataset)
WHERE $pilot IS NULL OR p.displayName STARTS WITH $pilot
OPTIONAL MATCH (d)-[:eg__hasVariable]->(v)
OPTIONAL MATCH (v)-[:INSTANCE_OF]->(c)
RETURN p.displayName AS pilot, d.uri AS d_uri, d.displayName AS dataset, d.eg__storedInDatabase AS db,
       v.uri AS v_uri, v.displayName AS variable, v.lakeMatch AS how, v.eg__unit AS unit,
       c.uri AS c_uri, c.displayName AS cls
"""


def main():
    p = parser("Export the ontology structure to GraphML")
    p.add_argument("--pilot", help="only this pilot")
    a = p.parse_args()
    g = nx.DiGraph()
    for r in run(a, QUERY, pilot=a.pilot.upper() if a.pilot else None):
        pk = pilot_key(r["pilot"])
        g.add_node("pilot:" + pk, label=pk, kind="pilot")
        g.add_node(r["d_uri"], label=r["dataset"], kind="dataset", pilot=pk, database=first(r["db"]) or "")
        g.add_edge("pilot:" + pk, r["d_uri"], kind="has_dataset")
        if r["v_uri"]:
            g.add_node(r["v_uri"], label=r["variable"], kind="variable", pilot=pk,
                       lake_match=first(r["how"]) or "none", unit=first(r["unit"]) or "")
            g.add_edge(r["d_uri"], r["v_uri"], kind="has_variable")
        if r["c_uri"]:
            g.add_node(r["c_uri"], label=r["cls"], kind="class")
            g.add_edge(r["v_uri"], r["c_uri"], kind="instance_of")
    path = output_path(f"structure{'_' + a.pilot.lower() if a.pilot else ''}.graphml")
    nx.write_graphml(g, path)
    print(f"{g.number_of_nodes()} nodes, {g.number_of_edges()} edges -> {path.relative_to(path.parents[1])}")


if __name__ == "__main__":
    main()
