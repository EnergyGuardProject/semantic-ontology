// Name: Average wind
MATCH (w:WindSeries)
RETURN avg(toFloat(w.wind)) AS AvgWind;
