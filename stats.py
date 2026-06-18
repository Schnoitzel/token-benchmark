"""
stats.py - kleine Statistik-Helfer fuer belastbare Aussagen.

Zweck: aus mehreren Wiederholungen (repeat) nicht nur einen Einzelwert, sondern
Median + Streuung zu berechnen. So wird sichtbar, wie stabil eine Zahl ist.

Nur Python-Standardbibliothek (statistics).
"""

import statistics


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
