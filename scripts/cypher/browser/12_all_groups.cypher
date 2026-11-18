// 12 · All sensor groups and where they belong
// pilot -> dataset <- sensor group (a group belongs to the datasets of its sensors). View: graph.
// For the size of each group, run 14_hierarchy_table.cypher or 06_sensor_groups.cypher.
MATCH path = (:Pilot)-[:mp__hasDataset]->(:Dataset)<-[:BELONGS_TO_DATASET]-(:MeasurementGroup)
RETURN path;
