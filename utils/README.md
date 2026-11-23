# Utils (build and load the graph)

What the Neo4j graph **depends on**. These are not examples: run them to build `ontology/all_pilots.owl` and load it.
For things to try, see [`scripts/`](../scripts/README.md).

```
utils/
├── ontology/   assemble and validate the ontology file (Python, terminal)
├── neo4j/      (re)load a Neo4j graph                  (bash, terminal)
└── cypher/     01 import · 02 mapping (run by neo4j/reload_ontology.sh)
```

The `ontology/` scripts need `rdflib` (`assemble.py`, `workbook_diff.py`, which also needs `openpyxl`) and `pyshacl` (`validate_shapes.py`). Credentials (`.env`) are not in git: see [`scripts/README.md`](../scripts/README.md) and `.env.example`.

---

## Rebuild and reload the ontology

```bash
# edit the hand-written sources: ontology/core.ttl and ontology/catalogue/*.ttl, then
python3 utils/ontology/assemble.py            # -> ontology/all_pilots.owl   (needs: pip install rdflib)
python3 utils/ontology/validate_shapes.py     # SHACL checks against ontology/shapes.ttl (needs: pip install pyshacl)

# when a partner sends a new workbook: report what it would change (applies nothing)
python3 utils/ontology/workbook_diff.py <pilot>

# empty, import and map a Neo4j container
utils/neo4j/reload_ontology.sh                 # the project's instance (container "neo4j-ontology")
utils/neo4j/reload_ontology.sh <container>     # any other Neo4j container
```

`reload_ontology.sh` empties the graph, imports the file and maps it (the graph is generated, so nothing is backed up). It copies the OWL file into the folder the
container mounts as `/import` (only needed for other containers; this project mounts `ontology/`), and logs everything to `output/logs/reload-<container>.txt`.

---

## Public read-only copy (for people without access to the server)

There are two Neo4j instances:

| Instance | Who | What |
|---|---|---|
| `neo4j-ontology` | you | private (reachable only from this machine), writable, with the plugins; the ontology is loaded here |
| `neo4j-public` | everyone | a read-only copy behind `https://ontology.energy-guard.eu`, with a shared password (`NEO4J_PUBLIC_PASSWORD` in `.env`) and **no plugins** |

On the public copy nobody can change or delete the graph, the `apoc` and `n10s` procedures do not exist (no file or
network access from queries), and a query running longer than 20 seconds is stopped. Neo4j Community cannot give a user
read-only rights, so anyone with the password could still create users or change the shared password in the `system`
database, which would only lock others out. Running `refresh_public.sh` rebuilds the copy and resets the password.

```bash
utils/neo4j/reload_ontology.sh      # load the ontology into the private instance
utils/neo4j/refresh_public.sh       # copy it into the public one (the private one stops for a few seconds, then is left as it was)
```

**One-time setting in nginx-proxy-manager**, proxy host `ontology.energy-guard.eu`:

1. *Details* tab: set *Forward Hostname* to `neo4j-public` (it was `neo4j`), *Forward Port* `7474`, and switch
   *Websockets Support* on.
2. *Advanced* tab, "Custom Nginx Configuration". The Neo4j Browser talks to Neo4j over a WebSocket at `/`, so route
   WebSocket requests there to the Bolt port and everything else to the web port:

```nginx
resolver 127.0.0.11 valid=30s;
location = / {
    set $target http://neo4j-public:7474;
    set $conn "";
    if ($http_upgrade = "websocket") { set $target http://neo4j-public:7687; set $conn upgrade; }
    proxy_pass $target;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $conn;
    proxy_set_header Host $host;
}
```

I tested this rule with a plain nginx in front of `neo4j-public`: the Browser page, the discovery reply and the query
interface answer, and a WebSocket handshake at `/` reaches Bolt. It has not been run inside nginx-proxy-manager itself.

**How users connect**
- **Python, curl, any script:** `https://ontology.energy-guard.eu/db/neo4j/query/v2` with user `neo4j` and the shared
  password; the explore kit (`scripts/explore/`) does this by default.
- **Neo4j Browser:** open `https://ontology.energy-guard.eu/browser/` and, if it asks for the address, use
  `neo4j+s://ontology.energy-guard.eu:443`, user `neo4j`, the shared password.

