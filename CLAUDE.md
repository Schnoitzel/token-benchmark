# CLAUDE.md — Token-Benchmark (Pi vs Claude Code)

> Lebendiges Statusdokument. Zuletzt aktualisiert: 2026-06-25.
> Vollständige Projekt-DNA: `AGENTS.md`. Methodik: `docs/methodik.md`.

## Aktueller Stand

Phasen 1–3 der Professionalisierung abgeschlossen (v0.3-phase3-show).
Session 2026-06-25: Token-Breakdown implementiert (Phasen A–D), Sonnet-ID-Bug
gefixt, Pi-Caching-Befund korrigiert dokumentiert.

**114 Unit-Tests grün.** Aktiver Plan: `docs/plans/2026-06-25-token-breakdown-n10.md`.

## Nächste Schritte (geordnet)

1. **Phase E — Referenzlauf n=10** (wartet auf User-Freigabe):
   ```bash
   python3 main.py --dry-run --repeat 10          # Trockentest
   python3 main.py --repeat 10                    # ~2–3h, ~$15–20
   python3 report.py                              # Bericht
   # JSON + Report nach docs/evidence/ kopieren
   ```

2. **Phase F — Quellen belegen** (nach Phase E):
   - Cache-TTL für Claude-4-Modelle in Anthropic-Docs verifizieren
   - Inferenzen vs. Fakten in `docs/methodik.md` und UI-Tooltips trennen
   - Quellen-Sektion ans Ende von `docs/methodik.md`

3. Multi-Slides im Präsentationsmodus (UI v2, niedrige Prio)

## Getroffene Entscheidungen

| Datum | Entscheidung | Wo dokumentiert |
|-------|--------------|-----------------|
| 2026-06-25 | n=10 Wiederholungen für Referenzlauf (Budget unkritisch) | Plan Phase E |
| 2026-06-25 | Pi-Caching modellabhängig (Haiku ≠ Sonnet/Opus) — bisherige Doku war falsch | `docs/adr/0001-pi-caching-modellabhaengig.md` |
| 2026-06-25 | Sonnet-ID: `claude-sonnet-4-5` → `claude-sonnet-4-6` (Bugfix) | `models.py` + `tests/test_models.py` |
| 2026-06-25 | Token-Breakdown in UI+Report: alle Felder einzeln, Overhead explizit | `static/index.html`, `report.py` |
| 2026-06-25 | Quellen-Pflicht: Fakten / Messbefunde / Inferenzen müssen getrennt belegt sein | Plan Phase F |
| 2026-06-18 | n=1 CLI-Default (günstig), n=5 Empfehlung für belastbare Zahlen | `docs/methodik.md` |
| 2026-06-18 | Einheitliche Kostenberechnung aus `pricing.py` für beide Harnesses | `pricing.py`, `core.py` |

## Bekannte Risiken / offene Lücken

- **Cache-TTL für Claude-4 nicht verifiziert:** Annahme 5 Min aus claude-3-Docs.
  Claude-4-Modelle könnten abweichen. → Phase F.
- **CC `sonnet`-Alias nicht protokolliert:** Welche genaue Modellversion CC's
  `sonnet`-Alias auflöst, steht nicht in der Provenienz-JSON. Erst nach
  Referenzlauf aus Raw-JSON prüfbar.
- **`medium-bash`-Task eingeschränkt vergleichbar:** Tool-Set ist OS-abhängig.
  Nicht für reinen Overhead-Vergleich geeignet. Noch nicht aus Aggregaten
  ausgeschlossen.
- **Pi Sonnet/Opus Kalt/Warm-Kostenvariation:** Bei n=1 misst man immer kalt
  (cache_write, teurer). Referenzlauf n=10 löst das via Median.

## Kennzahlen (Stand: Referenzlauf dcf6c6db, 2026-06-18)

| Modell | Pi Overhead | CC Overhead | Token-Faktor | Kosten-Faktor |
|--------|------------|-------------|-------------|---------------|
| Haiku 4.5 | 3.070 | 29.294 | **9,5×** | ~3,9× |
| Sonnet 4.6* | 3.069 | 28.465 | **9,3×** | ~6,8× |
| Opus 4.8 | 3.786 | 27.256 | **7,2×** | ~5,0× |

*Sonnet: alter Lauf mit `claude-sonnet-4-5`. Neuer Referenzlauf (Phase E) mit
`claude-sonnet-4-6` ausstehend.*

## Schnellstart

```bash
python3 server.py        # UI → http://localhost:8000 (Windows-Browser)
python3 -m unittest discover -s tests   # Tests
python3 main.py --dry-run               # Benchmark-Plan ohne API-Aufruf
```
