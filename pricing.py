"""
pricing.py - einheitliche Kostenberechnung.

WARUM: Pi und Claude Code melden ihre Kosten selbst - moeglicherweise mit
leicht unterschiedlichen Preistabellen, und unter einem OAuth-/Abo-Login kann
der gemeldete Wert geschaetzt oder 0 sein. Fuer einen WASSERDICHTEN
Kostenvergleich rechnen wir die Kosten daher fuer BEIDE Harnesses selbst aus -
aus EINER einzigen, offiziellen Preistabelle und den gemessenen Token-Zahlen.
So haengt der Kostenunterschied nachweisbar nur an den Tokens.

Preise = offizielle Anthropic-Listenpreise in USD pro 1 Mio Tokens.
Stand: Juni 2026. Bei Preisaenderungen NUR hier anpassen.

Cache-Aufschlaege (Anthropic 5-Minuten-Cache):
  cache_write = 1,25 x Input-Preis
  cache_read  = 0,10 x Input-Preis
"""

CACHE_WRITE_MULT = 1.25
CACHE_READ_MULT = 0.10

# Modell-Label -> (Input-Preis, Output-Preis) je 1 Mio Tokens (USD)
PRICES: dict[str, tuple[float, float]] = {
    "Haiku 4.5":  (1.00, 5.00),
    "Sonnet 4.6": (3.00, 15.00),
    "Opus 4.8":   (15.00, 75.00),
}


def compute_cost(
    model_label: str,
    input_tokens: int,
    output_tokens: int,
    cache_read: int,
    cache_write: int,
) -> float | None:
    """Kosten in USD aus Token-Zahlen. None, wenn das Modell unbekannt ist."""
    price = PRICES.get(model_label)
    if price is None:
        return None
    in_price, out_price = price
    total = (
        input_tokens * in_price
        + output_tokens * out_price
        + cache_write * in_price * CACHE_WRITE_MULT
        + cache_read * in_price * CACHE_READ_MULT
    )
    return total / 1_000_000


def cost_for_usage(model_label: str, usage) -> float | None:
    """Bequemer Wrapper: nimmt ein TokenUsage-Objekt (oder dict)."""
    if isinstance(usage, dict):
        return compute_cost(
            model_label,
            usage.get("input_tokens", 0),
            usage.get("output_tokens", 0),
            usage.get("cache_read", 0),
            usage.get("cache_write", 0),
        )
    return compute_cost(
        model_label,
        usage.input_tokens,
        usage.output_tokens,
        usage.cache_read,
        usage.cache_write,
    )
