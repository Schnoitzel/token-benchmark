"""
utils.py - gemeinsame Helfer, die von mehreren Modulen genutzt werden.

Vorher waren diese Funktionen in report.py / judge.py / main.py dupliziert
(teils mit leicht abweichendem Verhalten, z.B. fmt_cost mit .3f vs .4f).
Hier gibt es nun EINE Implementierung -> konsistente Anzeige, eine Quelle.
"""

import glob
import json


# --- Formatierung -----------------------------------------------------------

def fmt_cost(usd: float) -> str:
    """Kosten lesbar: sehr kleine Betraege als Millidollar (m$), sonst USD."""
    if usd < 0.001:
        return f"{usd * 1000:.4f}m$"
    return f"${usd:.5f}"


def fmt_n(n: float) -> str:
    """Ganzzahl mit Tausendertrennzeichen."""
    return f"{round(n):,}"


def ratio(a: float, b: float) -> str:
    """Verhaeltnis a/b als 'x.x' bzw. 'x.x weniger'. 'n/a' wenn 0 im Spiel."""
    if not a or not b:
        return "n/a"
    r = a / b
    return f"{r:.1f}x" if r >= 1 else f"{1 / r:.1f}x weniger"


# --- Fachliche Kennzahl -----------------------------------------------------

def overhead_tokens(usage: dict) -> int:
    """Harness-Overhead = mitgeschickter Kontext OHNE die Antwort.
    = Input + Cache-Read + Cache-Write (Output zaehlt NICHT)."""
    return (
        usage.get("input_tokens", 0)
        + usage.get("cache_read", 0)
        + usage.get("cache_write", 0)
    )


# --- Ergebnisdateien laden --------------------------------------------------

def latest_suite_path() -> str:
    """Pfad der neuesten Ergebnisdatei in results/. SystemExit, wenn keine da."""
    files = sorted(glob.glob("results/benchmark-*.json"))
    if not files:
        raise SystemExit("Keine Ergebnisdateien in results/ gefunden.")
    return files[-1]


def load_suite(path: str) -> dict:
    """Laedt eine Suite-JSON von einem konkreten Pfad."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)
