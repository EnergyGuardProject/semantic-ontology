// Name: Filter in series
MATCH (w:WindSeries)
WHERE toFloat(w.wind) < 40
RETURN w;
