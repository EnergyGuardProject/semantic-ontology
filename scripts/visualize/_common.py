"""Shared helpers for the visualisation scripts (connection, colours, terminal output)."""
import argparse
import os
import sys
from pathlib import Path

from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "output" / "visualizations"
MP = "https://www.energyguard.eu/ontology/merged-pilots#"
EG = "https://www.energyguard.eu/ontology#"

PILOT_COLORS = {
    "RDN": "#E57373", "CIEMAT": "#42A5F5", "BER": "#66BB6A", "CEA": "#26A69A",
    "CARTIF": "#9CCC65", "REA": "#FFA726", "ENGREEN": "#AB47BC",
}
CLASS_COLORS = {
    "Temperature": "#EF5350", "Pressure": "#5C6BC0", "Flow": "#29B6F6", "Power": "#FFCA28",
    "Energy": "#FFA000", "Current": "#AB47BC", "Voltage": "#7E57C2", "Speed": "#26C6DA",
    "SolarRadiation": "#FFEE58", "Composition": "#8D6E63", "Volume": "#4DB6AC", "Level": "#4DB6AC",
    "Timer": "#BDBDBD", "Efficiency": "#D4E157", "StateOfCharge": "#9CCC65", "State": "#78909C",
    "ControlSignal": "#EC407A", "Hydrogen": "#00ACC1", "Electrical": "#7E57C2",
    "Attributes": "#CFD8DC", "Other": "#ECEFF1",
}
GREY = "#B0BEC5"


def parser(description):
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--uri", default=os.environ.get("NEO4J_URI", "bolt://localhost:7689"),
                   help="Bolt URI (default: this project's instance bolt://localhost:7689; old live instance: bolt://localhost:7687)")
    p.add_argument("--user", default=os.environ.get("NEO4J_USER", "neo4j"))
    p.add_argument("--password", default=os.environ.get("NEO4J_PASSWORD", "REDACTED"))
    return p


def run(args, query, **params):
    """Run a read query and return a list of dicts."""
    with GraphDatabase.driver(args.uri, auth=(args.user, args.password)) as driver:
        records, _, _ = driver.execute_query(query, params, routing_="r")
        return [r.data() for r in records]


def first(value):
    """n10s stores most values as lists: take the first element."""
    if isinstance(value, list):
        return value[0] if value else None
    return value


def pilot_key(name):
    """'REA (Riga Energy Agency)' -> 'REA'"""
    return (name or "").split(" ")[0]


def class_key(measurement_type):
    """'TemperatureMeasurement' -> 'Temperature'"""
    return (measurement_type or "").replace("Measurement", "")


def class_color(measurement_type):
    return CLASS_COLORS.get(class_key(measurement_type), GREY)


def output_path(name):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUT_DIR / name


# ---- terminal styling (disabled when not a terminal) --------------------------------------
_TTY = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def style(text, *codes):
    if not _TTY:
        return str(text)
    return "".join(f"\033[{c}m" for c in codes) + str(text) + "\033[0m"


def bold(t):
    return style(t, 1)


def dim(t):
    return style(t, 2)


def green(t):
    return style(t, 32)


def yellow(t):
    return style(t, 33)


def red(t):
    return style(t, 31)


def cyan(t):
    return style(t, 36)


def bar(fraction, width=20):
    filled = round(fraction * width)
    return green("█" * filled) + dim("░" * (width - filled))
