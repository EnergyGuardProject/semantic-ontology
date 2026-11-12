// Name: Clean Labels for better viz
// This script adds meaningful labels and removes generic ones for visualization
// =========================
// 1️⃣ Add meaningful labels from secondary ones
// =========================
MATCH (n)
WITH n, [l IN labels(n) WHERE l STARTS WITH "ns"] AS meaningfulLabels
WHERE size(meaningfulLabels) > 0
CALL apoc.create.addLabels(n, meaningfulLabels) YIELD node
RETURN count(*) AS addedLabels;

// =========================
// 2️⃣ Remove generic labels for better visualization
// =========================
MATCH (n)
WHERE "Resource" IN labels(n)
REMOVE n:Resource
RETURN count(*) AS removedResource;

MATCH (n)
WHERE "owl__Class" IN labels(n)
REMOVE n:owl__Class
RETURN count(*) AS removedClasses;

MATCH (n)
WHERE "owl__NamedIndividual" IN labels(n)
REMOVE n:owl__NamedIndividual
RETURN count(*) AS removedIndividuals;

// =========================
// 3️⃣ Optional: add temporary "Viz" label for coloring
// =========================
MATCH (n)
WITH n, [l IN labels(n) WHERE l STARTS WITH "ns"] AS meaningfulLabels
WHERE size(meaningfulLabels) > 0
CALL apoc.create.addLabels(n, ["Viz_" + meaningfulLabels[0]]) YIELD node
RETURN count(*) AS vizLabels;

// =========================
// 4️⃣ Optional: inspect relationships
// =========================
MATCH (n)-[r]->(m)
WHERE any(l IN labels(n) WHERE l STARTS WITH "ns")
  AND any(l IN labels(m) WHERE l STARTS WITH "ns")
RETURN n, r, m
LIMIT 300;
