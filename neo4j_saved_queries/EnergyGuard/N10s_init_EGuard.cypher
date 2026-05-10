// Name: N10s init (EGuard)
CALL n10s.graphconfig.init({
  handleVocabUris: "SHORTEN",
  typesToLabels: true,
  namespacePrefixMappings: { eg: '<http://www.energyguard.eu/ontology#>' }
});
