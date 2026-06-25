# ADR-0001: Pi-Caching ist modellabhängig — Haiku ≠ Sonnet/Opus

- **Status:** Akzeptiert
- **Datum:** 2026-06-25
- **Kontext:** Referenzlauf `dcf6c6db` (Rohdaten in `docs/evidence/`)

## Entscheidung / Befund

Pi nutzt in der blank/ephemeren Konfiguration (`--no-session`) je nach Modell
unterschiedliches Caching-Verhalten:

| Modell | Pi run#0 | Pi run#1+ | Overhead-Tokens |
|--------|----------|-----------|-----------------|
| Haiku 4.5 | input=3070, cache=0 | input=3068, cache=0 | ~3.069 (stabil) |
| Sonnet 4.6 | input=3, cache_write=3066 | input=3, cache_read=1870, cache_write=1196 | ~3.069 (stabil) |
| Opus 4.8 | input=2, cache_write=3784 | input=2, cache_read=2504, cache_write=1280 | ~3.786 (stabil) |

**Token-Overhead ist in allen Fällen kalt/warm-stabil** (input + cache_read +
cache_write ≈ konstant). Nur die **Kosten** variieren:

- Pi Sonnet kalt (run#0): ~$0.012 — Pi Sonnet warm (run#1+): ~$0.005 (~2,3× Unterschied)
- Pi Haiku: immer ~$0.003 (kein Caching, kein Warm/Kalt-Effekt)

## Konsequenz für Messungen und Berichte

1. **Token-Overhead-Faktor** (die Kernaussage des Benchmarks) ist von diesem
   Befund **nicht betroffen** — er ist warm/kalt-stabil und das richtige Maß
   für den Harness-Vergleich.

2. **Kosten-Vergleich**: Für Sonnet/Opus **mindestens n=3 Wiederholungen**
   verwenden und Median nehmen — so sind beide Zustände (kalt + warm)
   repräsentiert. Bei n=1 misst man immer kalt (teurer).

3. **Methodik.md und Berichte** nennen diesen Befund explizit. Die frühere
   Aussage „Pi nutzt kein Prompt-Caching" gilt nur für Haiku 4.5.

## Offene Frage / Inferenz

Warum Haiku nicht cacht, Sonnet/Opus aber schon: möglicherweise modellspezifische
Cache-Schwellenwerte bei Anthropic (minimale Token-Anzahl für Caching-Aktivierung).
Nicht offiziell dokumentiert. Beobachtung, keine belegte Tatsache.
→ Quellen-Verifikation in Phase F (`docs/plans/2026-06-25-token-breakdown-n10.md`).
