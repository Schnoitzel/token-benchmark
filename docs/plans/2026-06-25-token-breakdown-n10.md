# Token-Breakdown & Vollständiger Referenzlauf (n=10)

- **Status:** In Progress
- **Date:** 2026-06-25
- **Branch/Worktree:** main (kleine, in sich geschlossene Schritte)

## Problem

1. **Sonnet-Modell-ID falsch:** `models.py` nutzt `claude-sonnet-4-5` (alt),
   Label sagt aber "Sonnet 4.6". Wenn CC's `sonnet`-Alias auf 4.6 auflöst,
   vergleichen wir gerade verschiedene Modelle. → Sofort-Fix erforderlich.

2. **Token-Felder zusammengefasst:** Die UI kollabiert `cache_read +
   cache_write` zu einem „Cache"-Wert. Der Report zeigt zwar alle Spalten,
   aber Streuung nur für Total+Kosten. Damit ist die eigentliche Mechanik
   (was kostet wie viel und warum) nicht auf einen Blick nachvollziehbar.

3. **Overhead als Kernaussage nicht explizit sichtbar:** Die Formel
   `overhead = input + cache_read + cache_write` — das Herzstück des
   Benchmarks — steht nirgends als eigene Zeile mit Wert.

4. **Kein belastbarer Vollreferenzlauf:** Bisher nur n=3 (Baseline) und
   n=1 (alle anderen Tasks). Für zitierfähige Ergebnisse brauchen wir
   n=10 über alle Tasks und Modelle.

## Scope

### In scope
- `models.py`: Sonnet-ID und Labels korrigieren (alle auf neueste verfügbare
  Version).
- `static/index.html`: KPI-Tabelle trennt `cache_write` und `cache_read`;
  neue Overhead-Zeile mit Formel; Kosten-Breakdown optional (Tooltip/Fußnote).
- `report.py`: Markdown-Tabelle zeigt Median (min–max) für alle Token-Felder
  einzeln, nicht nur für Total+Kosten. Overhead-Zeile ergänzt.
- Vollständiger Referenzlauf n=10, alle Tasks, alle 3 Modelle, beide
  Harnesses → in `docs/evidence/` versioniert.
- `docs/methodik.md`: Befund zu Pi-Caching bei Sonnet/Opus korrigieren
  (methodik.md behauptet fälschlicherweise "Pi cacht nicht").
- `tests/`: bestehende Tests grün halten; neue Tests für geänderte
  Report-Ausgabe und Modell-IDs.

### Out of scope
- Warm-Cache-Normierung (run#0 verwerfen) — ist eine separate Entscheidung,
  jetzt nicht.
- Neue Tasks oder Modelle jenseits der Korrektur.
- UI-Export, Präsentationsmodus (bereits vorhanden, unverändert).

## Approach

Schritte in strikter Reihenfolge, damit die Test-Suite nach jedem Commit grün
bleibt. Zuerst Modell-Fix (kritisch, kein Test-Aufwand), dann Backend
(report.py, Aggregat-Struktur), dann UI, zuletzt Referenzlauf + Doku.

Keine neuen Abhängigkeiten. Alle Änderungen stdlib-only (UI: reines HTML/JS).

## Design

### Neue/zu ändernde Dateien

| Datei | Art | Änderung |
|-------|-----|----------|
| `models.py` | ändern | `claude-sonnet-4-5` → `claude-sonnet-4-6`, Label "Sonnet 4.6" → "Sonnet 4.6" (bleibt, ID war falsch) |
| `report.py` | ändern | Alle Token-Felder mit Median (min–max): input, cache_write, cache_read, output, overhead, total, Kosten; Overhead-Zeile mit Formel |
| `static/index.html` | ändern | KPI-Tabelle: cache_write + cache_read getrennt; Overhead-Zeile; Kosten-Breakdown als Tooltip; Drill-down zeigt alle Felder mit Formel |
| `docs/methodik.md` | ändern | Pi-Caching-Befund korrigieren (Haiku: kein Cache; Sonnet/Opus: server-seitiger Cache ab run#1) |
| `tests/test_report.py` | ändern | Tests für neue Overhead-Zeile und erweiterte Streuung |
| `tests/test_models.py` | neu | Prüft dass Pi-Modell-ID != CC-Modell-ID-Alias, beide nicht leer |
| `docs/evidence/` | neu | Referenzlauf n=10 (JSON + Report) |

### Datenstruktur (unverändert — Backend liefert bereits alles)

`build_aggregates` in `stats.py` berechnet bereits `summary()` für alle
Felder inkl. `overhead`. Kein Backend-Umbau nötig.

### UI-Tabellen-Design (KPI-Hauptansicht)

```
          │ input │ cache↑ write │ cache↓ read │  output  │  Overhead*  │  Total  │ Kosten
──────────┼───────┼─────────────┼─────────────┼──────────┼─────────────┼─────────┼────────
Pi        │ 3.069 │      0      │      0      │     4    │   3.069     │  3.073  │ $0.003
Claude CC │    10 │    7.778    │   21.506    │    43    │  29.294     │ 29.337  │ $0.012
──────────┼───────┼─────────────┼─────────────┼──────────┼─────────────┼─────────┼────────
Faktor CC/Pi             –             –              –       9.5×                  3.9×

* Overhead = input + cache_write + cache_read (Formel als Tooltip)
```

Alle Werte = Median (n=10). Streuung (min–max) im Drill-down oder als
`title`-Tooltip auf der Zelle.

### Report-Tabellen-Design (Markdown)

```
| Modell | Harness | n | Input (med, min–max) | Cache↑W (med, min–max) | Cache↓R (med, min–max) | Output (med, min–max) | Overhead (med) | Total (med, min–max) | Kosten (med, min–max) | Dauer |
```

## Task Breakdown

### Phase A — Sofort-Fixes (kein Risiko)
- [x] A.1 `models.py`: `claude-sonnet-4-5` → `claude-sonnet-4-6`;
      Kommentar mit Verifikations-Datum + Pi-Modell-Liste-Quelle.
- [x] A.2 `tests/test_models.py`: Prüft pi_model != cc_model für alle
      Einträge; pi_model in bekannter Allowlist; kein Leerstring.
- [x] A.3 Suite grün (`python3 -m unittest discover -s tests`), commit.

### Phase B — Report.py: vollständiges Token-Breakdown
- [x] B.1 `report.py`: Markdown-Tabelle zeigt Median (min–max) für
      *alle* Token-Felder: input, cache_write, cache_read, output,
      overhead (berechnet), total, Kosten. Overhead-Spalte mit
      Formel-Fußnote.
- [x] B.2 `tests/test_report.py`: Tests für neue Spalten + Overhead-
      Berechnung im Report.
- [x] B.3 Suite grün, commit.

### Phase C — UI: Token-Breakdown in KPI + Drill-down
- [x] C.1 `static/index.html` KPI-Tabelle: `cache`-Spalte aufteilen in
      `cache↑ write` und `cache↓ read`; neue Spalte `Overhead` mit
      Formel-Tooltip; Faktor-Zeile zeigt Overhead-Faktor.
- [x] C.2 Drill-down: zeigt alle 5 Felder (input, cache_write,
      cache_read, output, overhead) mit Median + min–max + n.
      Kosten-Breakdown (was kostet welches Feld wie viel) als
      erläuternde Zeile.
- [x] C.3 JS via `node --check` validieren; manueller Smoke-Test mit
      vorhandenem Referenzlauf.
- [x] C.4 Suite grün, commit.

### Phase D — Methodik-Doku korrigieren
- [x] D.1 `docs/methodik.md`: Pi-Caching-Abschnitt präzisieren — Haiku
      cacht nicht (input only), Sonnet + Opus aktivieren server-seitigen
      5-Min-Cache ab run#1. Cache-Warm-Kalt-Kosteneffekt dokumentieren
      (Pi Sonnet: $0.012 kalt vs $0.005 warm). Erklärung warum
      Token-Overhead stabil ist, Kosten aber nicht.
- [x] D.2 Commit.

### Phase E — Vollständiger Referenzlauf n=10

- [ ] E.1 Trockentest: `python3 main.py --dry-run --repeat 10` →
      zeigt alle geplanten Läufe ohne API-Aufruf.
- [ ] E.2 Referenzlauf starten: alle Tasks, alle 3 Modelle, n=10.
      (Erwartete Laufzeit: 30–60 Min. Kosten: ~$15–20 geschätzt.)
- [ ] E.3 Report generieren, Ergebnisse prüfen: Streuung < 5% für
      Overhead-Tokens (erwartet), Kernaussage Token-Faktor ~7–9.5×
      reproduziert.
- [ ] E.4 JSON + Markdown-Report nach `docs/evidence/` kopieren,
      `docs/methodik.md` Mehrmodell-Tabelle mit neuen Zahlen aktualisieren.
- [ ] E.5 Commit + Push.

### Phase F — Quellen & Belege in `docs/methodik.md` ⬅ OFFEN

> **Kontext (festgehalten für nächste Session):**
> Alle Aussagen die im Tool getroffen werden müssen mit Quellen belegt sein.
> Unterscheide dabei drei Kategorien:

- [ ] F.1 **Anthropic-Fakten** (mit URL belegen):
  - Cache_write = 1,25× / cache_read = 0,10×
    → https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
  - Cache-TTL: in Docs als 5 Min für claude-3 dokumentiert;
    für **Claude-4-Modelle (Haiku 4.5, Sonnet 4.6, Opus 4.8) explizit
    verifizieren** — könnte abweichen. Bis zur Verifikation als
    "laut Anthropic-Docs, für claude-3 verifiziert" kennzeichnen.
  - Modellpreise (Haiku $1/$5, Sonnet $3/$15, Opus $15/$75 per MTok)
    → https://www.anthropic.com/pricing

- [ ] F.2 **Messbefunde** (auf eigene Evidence zeigen):
  - Pi ~3.069 Tokens, CC ~29.294 Tokens Overhead
    → docs/evidence/benchmark-dcf6c6db.json
  - Pi cacht nicht bei Haiku, cacht bei Sonnet/Opus ab run#1
    → Rohdaten dcf6c6db (run#0 vs run#1 Vergleich)
  - Nach Referenzlauf n=10: aktualisieren auf neue Evidence-Datei

- [ ] F.3 **Inferenzen** (explizit als solche kennzeichnen, NICHT als Fakten):
  - "Stabiler Kern ~21.506 Tokens persistent gecacht" → Beobachtung
    (cache_read=21506 bereits bei run#0), Ursache nicht offiziell
    dokumentiert. Formulierung: "Beobachtung aus Messdaten, Ursache unklar."
  - "Dynamischer Teil ~7.778 Tokens = session-spezifisch" → Inferenz
    aus konstantem Wert über alle Läufe, Inhalt unbekannt.
  - Cache-TTL für Claude-4-Modelle: Annahme aus claude-3-Docs,
    nicht direkt verifiziert.

- [ ] F.4 **Quellen-Sektion** ans Ende von `docs/methodik.md` anhängen
      (Anthropic-URLs + Verweis auf eigene Evidence-Dateien).

- [ ] F.5 **UI-Tooltips**: Fakten-Tooltips mit `[¹]`-Fußnote versehen,
      Inferenzen mit "(Beobachtung, nicht offiziell belegt)".

## Test Strategy

- `python3 -m unittest discover -s tests` nach jedem Phase-Abschluss.
- `node --check static/index.html` nach UI-Änderungen.
- Manuelle Verifikation: UI mit `docs/evidence/`-JSON laden, alle neuen
  Spalten prüfen.
- Für Referenzlauf (E): Plausibilitäts-Checks aus `test_live_measurement.py`
  nutzbar (`RUN_LIVE=1`).

## Risks & Open Questions

- **Pi `claude-sonnet-4-6` ID verfügbar?** → Pi-Liste zeigt sie als
  vorhanden (`claude-sonnet-4-6`). Trockentest in A.1 bestätigt das.
- **CC `sonnet`-Alias → welche genaue Version?** → Nicht protokolliert;
  nach dem Referenzlauf aus dem Raw-JSON prüfen.
- **Laufzeit E.2:** 9 Tasks × 3 Modelle × 2 Harnesses × 10 = 540 Läufe.
  Bei ~15s/Lauf: ~135 Min. Kann nachts laufen oder in Batches.
  Alternativ: erst Baseline n=10, dann Rest n=5 wenn Geduld fehlt.
- **UI-Tabelle wird breiter:** 7 Spalten statt 5 — auf kleinen Screens
  horizontales Scrollen nötig. Akzeptiert (Power-User-Tool).

## Definition of Done

- [ ] `models.py` nutzt `claude-sonnet-4-6` für Pi; Tests grün.
- [ ] Report-Tabelle zeigt für jeden Token-Typ Median (min–max).
- [ ] UI-KPI-Tabelle zeigt `cache_write` und `cache_read` getrennt,
      Overhead-Spalte mit Formel.
- [ ] Drill-down zeigt vollständigen Token-Breakdown mit Kosten-Anteil.
- [ ] `docs/methodik.md` beschreibt Pi-Caching korrekt.
- [ ] Referenzlauf n=10 in `docs/evidence/` versioniert.
- [ ] Alle Unit-Tests grün. JS valide.
- [ ] Alles committet und gepusht.
