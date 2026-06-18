"""
stats.py - kleine Statistik-Helfer fuer belastbare Aussagen.

Zweck: aus mehreren Wiederholungen (repeat) nicht nur einen Einzelwert, sondern
Median + Streuung zu berechnen. So wird sichtbar, wie stabil eine Zahl ist.

Nur Python-Standardbibliothek (statistics).
"""

import statistics
from collections import defaultdict


def median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def mean(values: list[float]) -> float:
    return statistics.mean(values) if values else 0.0


def minmax(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    return min(values), max(values)


def stdev(values: list[float]) -> float:
    """Stichproben-Standardabweichung. 0, wenn weniger als 2 Werte."""
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values)


def iqr(values: list[float]) -> float:
    """Interquartilsabstand (Q3-Q1, inklusive Methode). 0 bei < 2 Werten."""
    if len(values) < 2:
        return 0.0
    q = statistics.quantiles(values, n=4, method="inclusive")
    return q[2] - q[0]


def rel_spread(values: list[float]) -> float:
    """Relative Spanne = (max-min)/median. 0, wenn < 2 Werte oder Median 0.
    Anschauliches Mass dafuer, wie stark die Werte (relativ) schwanken."""
    if len(values) < 2:
        return 0.0
    m = median(values)
    if not m:
        return 0.0
    return (max(values) - min(values)) / m


def summary(values: list[float]) -> dict:
    """Buendelt alle Masse in ein dict (fuer JSON/Report/UI).

    Felder: n, median, min, max, mean, stdev, iqr, rel_spread.
    Robust gegen leere Liste und Einzelwert.
    """
    lo, hi = minmax(values)
    return {
        "n": len(values),
        "median": median(values),
        "min": lo,
        "max": hi,
        "mean": mean(values),
        "stdev": stdev(values),
        "iqr": iqr(values),
        "rel_spread": rel_spread(values),
    }


# Metriken, die je Kombination aggregiert werden (Feldname -> Funktion auf result-dict)
_METRICS = {
    "total_tokens": lambda r: r["usage"]["total_tokens"],
    "input_tokens": lambda r: r["usage"]["input_tokens"],
    "output_tokens": lambda r: r["usage"]["output_tokens"],
    "cache_read": lambda r: r["usage"]["cache_read"],
    "cache_write": lambda r: r["usage"]["cache_write"],
    "overhead": lambda r: (r["usage"]["input_tokens"]
                           + r["usage"]["cache_read"]
                           + r["usage"]["cache_write"]),
    "cost_usd": lambda r: r["usage"]["cost_usd"],
    "duration_ms": lambda r: r["duration_ms"],
}


def build_aggregates(results: list[dict]) -> list[dict]:
    """Aggregiert die Roh-Ergebnisse je (task_id, model_label, harness) zu
    Median+Streuung pro Metrik. Fehlerhafte Laeufe werden ausgeschlossen.

    Liefert eine Liste von dicts mit: task_id, model_label, task_complexity,
    harness, n, metrics={metrik: summary(...)}. So koennen UI und Report die
    belastbaren Zahlen anzeigen, ohne sie selbst neu zu berechnen.
    """
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for r in results:
        if r.get("error"):
            continue
        groups[(r["task_id"], r["model_label"], r["harness"])].append(r)

    out = []
    for (task_id, model_label, harness), rows in groups.items():
        metrics = {
            name: summary([fn(r) for r in rows]) for name, fn in _METRICS.items()
        }
        out.append({
            "task_id": task_id,
            "model_label": model_label,
            "task_complexity": rows[0].get("task_complexity"),
            "harness": harness,
            "n": len(rows),
            "metrics": metrics,
        })
    return out
