// Name: Filter rows
// Query example filtering multiple series
MATCH (w:WindSeries), (s:`Solar Series`), (n:`Netload Series`)
WITH w, s, n
WHERE toFloat(w.wind) < 40
  AND toFloat(s.solar) < 20
  AND toFloat(n.`Net load`) > 0
RETURN toFloat(w.wind) AS Wind,
       toFloat(s.solar) AS Solar,
       toFloat(n.`Net load`) AS `Net load`
LIMIT 100;
