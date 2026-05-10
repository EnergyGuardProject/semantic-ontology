// Name: List all classes
MATCH (c)
WHERE any(l IN labels(c) WHERE l STARTS WITH "ns") OR "Dataset" IN labels(c)
RETURN DISTINCT labels(c) AS ClassLabels
ORDER BY ClassLabels;
