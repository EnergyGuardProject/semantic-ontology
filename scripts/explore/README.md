# Explore the EnergyGuard ontology (no Cypher needed)

A small, self-contained kit to try out the EnergyGuard ontology stored in Neo4j.
It only **reads** the graph. Nothing else from the repository is needed.

| File | What it is |
|---|---|
| `explore_ontology.ipynb` | step-by-step notebook: pilots, datasets, measurement types, variables, one variable in detail |
| `eg.py` | the helper the notebook uses: plain functions that hide the Neo4j queries |
| `requirements.txt` | Python packages needed |
| `.env.example` | template for the connection settings (copy to `.env`) |

## You need
- Python 3.10+
- The **password** of the public read-only Neo4j (user `neo4j`), from whoever gave you this folder. The address is
  `https://ontology.energy-guard.eu`; it works from anywhere, with no tunnel and no extra software. The copy is
  read-only: you can look at anything but cannot change it.
- (Optional, on the server or through an SSH tunnel) the private Neo4j over Bolt: `NEO4J_URI=bolt://localhost:7687`
  (needs `pip install neo4j`).

## Setup
```bash
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
jupyter notebook explore_ontology.ipynb
```
Run the cells from the top. The "Connect" cell uses the settings in a file called `.env` next to the notebook
(copy `.env.example` to `.env` and fill in the address and password). If there is no `.env`, it asks for them.
You can also set `NEO4J_URI`, `NEO4J_USER` and `NEO4J_PASSWORD` as environment variables.

> **Sharing this folder?** Do not include your own `.env` (it holds a password). Send `.env.example` instead.
VS Code also works: open the notebook and choose the `venv` kernel (`pip install ipykernel` if asked).

## Without the notebook
```python
import eg
eg.connect("https://ontology.energy-guard.eu", "neo4j", "<password>")   # or set the NEO4J_* variables
eg.pilots()                         # which pilots exist and how big they are
eg.datasets("hydrogen")             # datasets mentioning a word (no argument: all)
eg.measurement_types()              # every measurement type (optionally for one pilot)
eg.equipment()                      # every piece of equipment and the variables it hosts
eg.variables(pilot="BER")          # every variable of one pilot (add a measurement type: eg.variables("Temperature", "BER"))
eg.find("storage tank")             # search variables by words in their name or description
eg.variable("TT-D101")              # what it is and its data lake sensor id
eg.describe("TT-D101")              # print everything the ontology knows about it
eg.tree("BER")                      # one pilot as pilot -> datasets -> variables
eg.readings_sql("TT-D101")          # SQL to fetch its readings (it does not connect to the data lake)
```
Every function that returns a result gives a list of dicts (wrap it in `pandas.DataFrame` to see a table).

## What the ontology is
A **catalogue**: it says which datasets and variables exist for each pilot and where their numbers live in the data
lake. It does not contain the measurements themselves.
Tree: **pilot → dataset → variable**; each variable also has a **measurement type** (Temperature, Pressure, ...), a unit, and often the **equipment** that hosts it.
