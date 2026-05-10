// Name: Validate n10s installation
SHOW PROCEDURES YIELD name
WHERE name STARTS WITH 'n10s'
RETURN name ORDER BY name;
