// 04 · The pilots and their datasets
// View: graph. Big nodes = pilots, small = datasets.
MATCH path = (:Pilot)-[:HAS_DATASET]->(:Dataset)
RETURN path;
