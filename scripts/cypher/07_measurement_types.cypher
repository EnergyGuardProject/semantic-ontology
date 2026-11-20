// 07 · The shared measurement types (sosa:ObservableProperty) and their QUDT quantity kinds
// View: graph. Every type belongs to the EnergyGuard measurement-type scheme and, where QUDT has one, to a quantity kind.
MATCH (t:MeasurementType)
OPTIONAL MATCH scheme = (t)-[:skos__inScheme]->(:Resource)
OPTIONAL MATCH kind = (t)-[:qudt__hasQuantityKind]->(:Resource)
RETURN t, scheme, kind;
