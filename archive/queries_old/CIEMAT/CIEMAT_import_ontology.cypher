// Name: CIEMAT import ontology
CALL n10s.rdf.import.fetch(
  "file:///C:/Users/atzortzis/OneDrive%20-%20EPU-NTUA/Documents/ΕPU%20Projects/EGuard/ontology/ontology_v3/ciemat_refactored_v3.owl",
  "RDF/XML",
  { handleVocabUris: "SHORTEN" }
);
