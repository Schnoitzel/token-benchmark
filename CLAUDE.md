# CLAUDE.md — Token-Benchmark (Pi vs Claude Code)

> Lebendiges Statusdokument. Zuletzt aktualisiert: 2026-06-30.
> Vollständige Projekt-DNA: `AGENTS.md`. Methodik: `docs/methodik.md`.

## Aktueller Stand

Phasen 1–3 der Professionalisierung abgeschlossen (v0.3-phase3-show).
- **2026-06-25:** Token-Breakdown (Phasen A–D), Sonnet-ID-Bug gefixt, Pi-Caching-Befund korrigiert.
- **2026-06-29:** Referenzlauf n=10 gefahren (540 Runs, `results/benchmark-d1b7ef63.json`) +
  Resume-Funktion + atomisches Schreiben. **Befund:** `medium-bash` war environment-asymmetrisch
  → durch fairen Task ersetzt (ADR-0003). → `medium-bash` läuft deshalb neu.
- **2026-06-30:** Präsentation/Doku/Container geplant (Summer Show). Externe `Token-Benchmark-v2.pptx`
  hatte korrupte Kosten (`$`→`/bin/bash` durch Shell-Expansion) + Live-Demo-Titel out-of-frame
  → repariert als `Token-Benchmark-v3.pptx` (auf User-Desktop, nicht im Repo). Stil + Inhalt
  der neuen Präsi abgestimmt. **Noch nicht implementiert** (gated).
- **2026-06-30 (Daten-Check):** Referenzlauf `benchmark-d1b7ef63.json` (540 Runs, n=10) gesichtet:
  sauber, Sonnet-ID korrekt (`claude-sonnet-4-6`), 2 Pi-Timeouts. **Neuer Befund — Plattform-
  Asymmetrie (ADR-0004):** `claude` ist hier ein **Windows**-Binary (`/mnt/c/.../npm/claude`),
  `pi` läuft **Linux/WSL**. Verfälscht alle Tool-/Multi-Turn-Tasks (`medium-bash` 7–16 Turns,
  `simple-code` 2; Rest `num_turns=1` = sauber). **Overhead ~8× bleibt gültig** (Single-Turn).
  Real-Task: Pi liegt **nicht** durchgängig vorne (Haiku teurer+langsamer als CC). → `medium-bash`
  muss **im Container** (gleiches OS) neu gefahren werden, bevor es als Tool-Vergleich zählt.

- **2026-06-30 (Umsetzung):** Container gebaut (`Dockerfile`, `docker/`) → `medium-bash` darin
  **fair neu gefahren** (n=10, `benchmark-c066a92f.json`, **4,7–6,8×** statt Windows-Artefakt
  14–22×). Per Merge (ADR-0005, `merge_suites.py`) in die faire **Gesamtsuite
  `benchmark-9a72151a.json`** (540 Runs) eingearbeitet; `results/` aufgeräumt (Backup `/tmp`).
  UI in **SelectLine-Brand** umgebaut (`static/index.html`, `static/fonts/`), Drill-down
  „Wie erhoben?" entfernt. **Präsentation gebaut** (`docs/praesentation/`,
  `Token-Benchmark-SummerShow.pptx`, 8 Folien) — Folie-4-Chart als brand-konformes gerendertes
  PNG (Edge headless). Im visuellen Review.

**125 Unit-Tests grün** (3 Live-Tests opt-in übersprungen).
Aktiver Plan: `docs/plans/2026-06-30-praesentation-und-doku.md`.

## Nächste Schritte (geordnet)

1. **Präsi-Review abschließen** (visuell in PowerPoint, Datei auf User-Desktop) + Live-Demo
   proben. Offene Detailfrage: Logo aufs Folie-4-Chart-PNG einbauen?
2. **2 PDFs bauen** (DOC1 Methodik & Ergebnisse, DOC2 Nutzung & Ausblick) — Quelle `9a72151a`.
3. Optional: `judge.py` für `9a72151a` (blinder Qualitätsbeleg, falls Zeit).
4. **Phase F — Quellen belegen:** Cache-TTL Claude-4 verifizieren; Inferenzen vs. Fakten in
   `docs/methodik.md` trennen; Quellen-Sektion ergänzen.
5. **`/sync`** für Git-Backup des heutigen Stands (Container, Merge, Brand-UI, Präsi, ADR-0005).
6. Multi-Slides im Präsentationsmodus (UI v2, niedrige Prio).

## Getroffene Entscheidungen

| Datum | Entscheidung | Wo dokumentiert |
|-------|--------------|-----------------|
| 2026-06-30 | Daten-Merge (Option A): faire Gesamtsuite `9a72151a` (Single-Turn Windows + Tool Container), gemischte Provenienz gekennzeichnet | `docs/adr/0005-...md`, `merge_suites.py` |
| 2026-06-30 | UI im SelectLine-Brand (hell default, Inter Tight, Anthrazit/Orange); Drill-down „Wie erhoben?" entfernt (Erhebung kommt in die Präsi) | `static/index.html`, `static/fonts/` |
| 2026-06-30 | Präsi-Strategie: 540er-Suite = belastbare Truth, Real-Task bestätigt; Folie 4 als gerendertes Brand-Chart (PNG), Modellfarben = Anthrazit-Staffelung (kein Orange in Balken) | `build_presentation_v2.py`, `docs/praesentation/folie4-chart.html` |
| 2026-06-30 | Präsi schlank halten (≤10 min): Kategorien statt Prompts, Tabellen → Doku, Grafiken + Take-aways | Plan `2026-06-30-praesentation-und-doku.md` |
| 2026-06-30 | Doku als 2 PDFs: (1) Methodik & Ergebnisse, (2) Nutzung & Ausblick | selber Plan |
| 2026-06-30 | Container für Kollegen: Self-Login je Nutzer, **ohne** Real-Task (Repo nicht teilbar); synthetische Tasks ohne Setup lauffähig | selber Plan |
| 2026-06-30 | Ergebnis-Chart: gruppiert nach Harness, Farbe=Modell (zeigt beide Vergleiche); je Chart Einheit + n | selber Plan |
| 2026-06-30 | Plattform-Asymmetrie CC=Windows/Pi=Linux → betrifft alle Tool-/Laufzeit-Vergleiche, NICHT Overhead ~8×; faire Tool-Messung nur im Container | `docs/adr/0004-plattform-asymmetrie-cc-windows-pi-linux.md` |
| 2026-06-30 | Keine pauschale „Pi durch mehr Turns günstiger"-Aussage — hält nicht durchgängig (Haiku-Real-Task widerlegt) | selber Plan |
| 2026-06-29 | `medium-bash` ersetzt (environment-agnostisch), alter Lauf dadurch teilweise hinfällig | `docs/adr/0003-medium-bash-environment-asymmetrie.md` |
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
- ~~**CC `sonnet`-Alias nicht protokolliert**~~ ✅ geklärt (2026-06-30): raw von
  `benchmark-d1b7ef63.json` zeigt `claude-sonnet-4-6` und `claude-opus-4-8` — korrekt.
  (Das nebenher auftauchende `claude-haiku-4-5` ist CCs interner Hintergrund-Helfer.)
- **Plattform-Asymmetrie (ADR-0004):** CC = Windows-Prozess, Pi = Linux/WSL. Alle
  Tool-/Multi-Turn-Tasks (`medium-bash`, teils `simple-code`, Real-Task) sind dadurch
  bei Tokens/Turns/Laufzeit verfälscht. Overhead ~8× (Single-Turn) bleibt sauber.
  Faire Tool-Messung erst im Container (beide gleiches OS).
- ~~**`medium-bash` eingeschränkt vergleichbar (14–22×).**~~ ✅ erledigt (2026-06-30): fair im
  Container neu erhoben (4,7–6,8×) und per Merge (ADR-0005) in `9a72151a` eingearbeitet.
- **Gemischte Provenienz in `9a72151a` (ADR-0005):** Single-Turn aus Windows-Lauf (claude
  2.1.170), `medium-bash` aus Container (claude 2.1.196). Für Overhead-Vergleich irrelevant,
  maschinenlesbar gekennzeichnet. Saubere Option C (kompletter Container-Lauf) bleibt offen.
- **Build-Artefakte im Projekt-Root:** `merge_suites.py`, `build_presentation_v2.py`,
  `qa_presentation.py` liegen im Root (außerhalb der AGENTS.md-Struktur). `merge_suites.py` ist
  ein legitimes Tool; Präsi-Build-Skripte ggf. später nach `docs/praesentation/`. Präsi-Build
  nutzt `python-pptx` + Windows-Edge (nicht stdlib) — nur Build-Zeit, kein Tool-Runtime.
- **Pi Sonnet/Opus Kalt/Warm-Kostenvariation:** Bei n=1 misst man immer kalt
  (cache_write, teurer). Referenzlauf n=10 löst das via Median.
- **„Mehr Turns → günstiger" ist NICHT robust:** Real-Task (n=5) zeigt das nur teils
  (Sonnet/Opus), bei Haiku machte Pi ~47 Turns und war *nicht* günstiger. Robuste
  Aussage bleibt der Pro-Anfrage-Overhead (~8× Token). Vor Präsi mit finalen Daten prüfen.
- **Real-Task = n=5, Einzelszenario:** ehrlich kennzeichnen; nur erwähnen wenn es sich
  mit den synthetischen Ergebnissen deckt, sonst Abweichung explizit nennen.

## Kennzahlen (Stand: faire Gesamtsuite `9a72151a`, n=10, 2026-06-30)

Overhead pro Anfrage (`baseline-overhead`):

| Modell | Pi Overhead | CC Overhead | Token-Faktor | Kosten-Faktor |
|--------|------------|-------------|-------------|---------------|
| Haiku 4.5 | 3.453 | 29.075 | **8,4×** | 3,4× |
| Sonnet 4.6 | 3.453 | 28.250 | **8,2×** | 5,2× |
| Opus 4.8 | 4.319 | 26.955 | **6,2×** | 3,6× |

Tool-Aufgabe fair (`medium-bash`, Container, ADR-0005): Pi 7.736 / 7.738 / 9.530 vs.
CC 52.381 / 50.482 / 44.830 → **6,8× / 6,5× / 4,7×** (Haiku/Sonnet/Opus).

## Schnellstart

```bash
python3 server.py        # UI → http://localhost:8000 (Windows-Browser)
python3 -m unittest discover -s tests   # Tests
python3 main.py --dry-run               # Benchmark-Plan ohne API-Aufruf
```
