# Präsentation (Summer Show) + Doku-Abgabe + Container-Distribution

- **Status:** In Umsetzung — Go erteilt 2026-06-30. Container + faire `medium-bash`-Daten liegen vor (ADR-0004/0005); Präsentation gebaut, im visuellen Review. PDFs offen.
- **Date:** 2026-06-30
- **Branch/Worktree:** main (kleine, in sich geschlossene Schritte)

## Ziel

Aus dem POC drei Artefakte ableiten, klar getrennt:

1. **Präsentation** — schlank, visuell, große Take-aways. Harte Grenze: **≤ 10 min inkl. Live Demo**.
2. **Doku (2 PDFs)** — alle Details als Beleg + Anleitung/Ausblick für Kollegen.
3. **Container-Version** — damit Kollegen selbst Tests fahren können (ohne Real-Task).

## Bestätigte Fakten (Stand 2026-06-30)

- **Stichproben:** alle synthetischen Tasks **n=10**; **Real-Task n=5** je Harness/Modell.
- **Versuchsaufbau:** 2 Harnesses (Pi, Claude Code) × 3 Modelle (Haiku 4.5, Sonnet 4.6, Opus 4.8)
  × 9 synthetische Tasks (5 Komplexitätsstufen) + 1 Real-Task. Leere Sandbox für synthetische
  Tasks, echtes Repo für Real-Task. Kosten einheitlich aus Tokens (`pricing.py`).
- **Task-Kategorien** (für die Versuchsaufbau-Folie, ohne Prompts vorzulesen):
  Wissen/Fakten · Code schreiben · Erklären/Design · **Tool-Nutzung (Shell)** · **Real-Task (echtes Repo)**.
- **Keine Pfad-Abhängigkeiten in den 9 synthetischen Tasks** (verifiziert in `tasks.py`):
  reine Text-Prompts, nichts muss im Container angelegt werden. Einziger Pfad: Real-Task `repo_dir`.
- **Bekannte Korruption in der alten PPTX** (`$`→`/bin/bash` durch Shell-Expansion) ist in
  `Token-Benchmark-v3.pptx` bereits behoben; die neue Präsi wird ohnehin neu gebaut.

## ⚠️ Blocker / offene Daten

- **Plattform-Asymmetrie entdeckt (ADR-0004, 2026-06-30):** `claude` ist in dieser Umgebung ein
  **Windows-Binary** (`/mnt/c/.../npm/claude`), `pi` läuft **Linux/WSL**. Betrifft **alle Tool-/
  Multi-Turn-Tasks** (Tokens, Turns, Laufzeit verfälscht), **nicht** die Overhead-Kernzahl (~8×,
  beruht auf Single-Turn-Tasks `num_turns=1`).
- ~~**`medium-bash`-Re-Run noch nicht zitierfähig (Plattform-Asymmetrie).**~~ ✅ **erledigt
  (2026-06-30):** im Container fair neu gefahren (`benchmark-c066a92f.json`, n=10, 0 Fehler) →
  konsistent **4,7–6,8×** (statt Windows-Artefakt 14–22×). Per Merge (ADR-0005) in die faire
  Gesamtsuite `benchmark-9a72151a.json` eingearbeitet. Der „14–22×"-Ausreißer war ein Messartefakt.
- **Real-Task ehrlich kennzeichnen:** n=5, Einzelszenario, **plattform-asymmetrisch** (Repo unter
  `/mnt/c`, CC nativ Windows, Pi über langsame WSL-Brücke). Verifiziert: **Pi liegt NICHT
  durchgängig vorne** — bei Haiku teurer *und* langsamer als CC, nur bei Opus klar vorne.
  Regel für die Präsi:
  - **Keine** „Pi gewinnt trotz Nachteil"-Aussage (Daten widerlegen das bei Haiku).
  - Belastbare Botschaft: „Über eine ganze, mehrstufige Aufgabe hängt die Effizienz vom Modell
    ab (mal Pi, mal CC vorne); der robuste Befund bleibt der **Overhead pro Anfrage ~8×**."
  - Real-Task nicht neu fahren (zu teuer) — nur mit diesem Vorbehalt erwähnen.

## Inhalt: Präsentation (Ziel 7 Folien / ~10 min)

| # | Folie | Kern | ~Zeit |
|---|-------|------|------|
| 1 | Titel | — | 15 s |
| 2 | **Pi vs. Claude Code + die Frage** | Was unterscheidet die Harnesses (minimalistisch vs. feature-reich) → daraus folgt der Overhead. Die Frage: wie groß ist der Unterschied bei gleicher Qualität? | 75 s |
| 3 | **Versuchsaufbau** | Kategorien (Wissen·Code·Tools·Real), 2×3×Tasks, n=10 (Real n=5), Sandbox, eine Preisliste. „Genau nachlesbar → Doku" | 75 s |
| 4 | **Tokens + Kosten** | Doppel-Chart (Option 2: gruppiert nach Harness, Farbe=Modell) + Annotation **woher der Overhead kommt** | 90 s |
| 5 | **Qualität gleich** (+ Real-Task benennen) | Blindtest + reales Szenario: kein bedeutsamer Qualitätsunterschied | 75 s |
| 6 | **Live Demo** | localhost:8000 (Drill-down, Breakdown) | ~3 min |
| 7 | **Fazit / Kernaussagen** | 3 Take-aways | 45 s |

### Inhaltlich neu (vom Nutzer gewünscht): „Woher kommt die erhöhte Token-Nutzung?"

Auf Folie 2 (Unterschied der Harnesses) + Folie 4 (Annotation) erklären:

- **Pro Anfrage (robust, n=10):** Claude Code schickt einen **großen, feature-reichen System-Prompt
  + viele Tool-Definitionen** bei *jeder* Anfrage (~29k Tokens). Pi ist minimalistisch (~3,5k).
  Das ist die strukturelle Quelle des Overheads — nicht das Modell, sondern der Harness.
- **Über eine ganze Aufgabe (mehrere Turns):** Gesamttokens ≈ Overhead-pro-Turn × Anzahl Turns + eigentliche Arbeit.
  Der Harness mit dem größeren Pro-Turn-Overhead zahlt bei *jedem* Tool-Call „Steuer".
- **Pi „mehr Runs, trotzdem günstiger" — VORSICHT, mit finalen Daten prüfen:**
  Diese Aussage hält **nicht durchgängig**. Real-Task-Beobachtung (n=5, verifizieren!):
  - Haiku: Pi ~47 Turns vs. CC 19 — Pi macht deutlich mehr Schritte, war dort **nicht** günstiger
    (Pi $0,128 vs. CC $0,120, quasi gleichauf).
  - Sonnet: gleiche Turns (13/13), Pi etwas günstiger ($0,190 vs. $0,219).
  - Opus: Pi viel günstiger ($1,222 vs. $2,584).
  → **Für die Präsi nur das sagen, was die Daten tragen.** Saubere Botschaft:
  „Der Overhead pro Anfrage ist strukturell ~8× größer; ob sich das über mehr Turns ausgleicht,
  hängt vom Modell ab." Keine pauschale „Pi ist durch mehr Runs immer günstiger"-Aussage.
  (Final entscheiden, wenn `medium-bash`-Re-Run + Real-Task-Zahlen bestätigt sind.)

### Diagramm-Stil (entschieden)
- Kombinierte Ergebnis-Folie: zwei Panels nebeneinander (Tokens | Kosten), **gruppiert nach Harness,
  Farbe = Modell** (Option 2). Gemeinsame Modell-Legende. Pro Panel eine kleine Präzisierungs-Zeile
  (was genau + Einheit + n). Mockup: `/tmp/pi-design-preview-deck.html`.
- Offen: native PowerPoint-Charts (editierbar) vs. statische Balken — beim Bauen entscheiden.

## Inhalt: Doku — 2 PDFs

**PDF 1 — Methodik & Ergebnisse (Beleg)**
- Methodik komplett: Flags, Sandbox, Token-Felder, verifizierte Cache-Semantik.
- Vollständige Task-Liste **mit allen Prompts** (das, was die Präsi nur als Kategorie nennt).
- Volle Token- & Kosten-Tabellen je Task × Modell × Harness (Median + Streuung).
- ADR-0001 (Pi-Caching modellabhängig), ADR-0002 (turn_end-Summierung), ADR-0003 (medium-bash-Fairness).
- Real-Task: Token/Kosten + Qualitätsmatrix (4 Bugs × Läufe) + Analyse, **mit n=5-Hinweis**.
- Einschränkungen & offene Fragen (Cache-TTL, CC-Kern, Pi-Caching-Ursache).
- Quelle: aus vorhandenen `docs/` zusammengezogen + neue Zahlen.

**PDF 2 — Nutzung & Ausblick (für Kollegen)**
- Wie man das Tool startet (UI `python3 server.py` / CLI `main.py`), Modelle/Tasks anpassen.
- Container-Anleitung (Login pro Nutzer selbst — siehe unten).
- Was bewusst fehlt (Real-Task) und warum.
- Nächste Schritte: Multi-Slides, mehr/billigere Modelle, Quellen-Phase F.

## Inhalt: Container-Distribution (+ methodische Messumgebung)

> **Doppelrolle (ab ADR-0004):** Der Container ist nicht nur Distributions-Mittel für Kollegen,
> sondern die **faire Messumgebung** für Tool-Tasks — beide Harnesses laufen darin im **selben**
> Linux-OS, was die Windows/Linux-Asymmetrie beseitigt. Der `medium-bash`-Neulauf passiert hier.

Entscheidungen (mit Nutzer abgestimmt 2026-06-30):
- **Login:** Jeder Kollege hat eigenen Zugang und loggt sich **im Container selbst** ein
  (Pi + Claude Code je OAuth) — kein Key-Reinreichen nötig, kein Blocker.
- **Real-Task:** in der Kollegen-Version **weglassen** (Repo nicht teilbar). Tool muss
  Real-Tasks sauber überspringen, wenn `repo_dir` fehlt (ist bereits so vorgesehen — verifizieren).
- **Synthetische Tasks:** laufen ohne Setup (keine Pfad-Deps, verifiziert). Nichts vorzubereiten.
- **Offen beim Bauen:** Dockerfile (Python 3.10+, `pi` + `claude` CLI installieren), README für
  Login + Start, Port 8000 exposen. Prüfen: laufen beide CLIs headless im Container, und wie
  persistiert die OAuth-Session über Container-Neustarts.

## Schritte (erst nach Daten + Go abarbeiten)

- [x] **D0 — Daten gesichtet (2026-06-30):** Referenzlauf `benchmark-d1b7ef63.json` (540 Runs, n=10)
      geprüft — sauber, Sonnet-ID korrekt (`claude-sonnet-4-6`), nur 2 Pi-Timeouts. **Befund:**
      Plattform-Asymmetrie (ADR-0004) → `medium-bash`-Re-Run noch nicht fair. „mehr Turns/günstiger"
      gegen Daten geprüft: hält **nicht** (Real-Task Haiku → Pi teurer). Overhead ~8× bestätigt.
- [x] **C1 — Container** (2026-06-30): `Dockerfile` (node:24-bookworm-slim, Python, `pi`+`claude`
      beide nativ Linux), `docker/run.sh`, `docker/README.md`, `.dockerignore`. Credentials-Import
      statt headless-OAuth (`import-creds`), läuft als non-root User `node`. Real-Task-Skip verifiziert.
- [x] **D1 — `medium-bash` im Container neu gefahren** (2026-06-30): n=10, 60 Runs, 0 Fehler
      → `benchmark-c066a92f.json`, Faktor 4,7–6,8×. CC-Turns 2–5 (statt 7–16).
- [x] **D2 — Merge zur fairen Gesamtsuite** (2026-06-30, ADR-0005): `merge_suites.py` →
      `benchmark-9a72151a.json` (540 Runs); `results/` aufgeräumt; gemischte Provenienz gekennzeichnet.
- [x] **P1–P5 — Präsentation gebaut** (2026-06-30): `Token-Benchmark-SummerShow.pptx` (8 Folien,
      SelectLine-PPT-Template via `python-pptx`, `build_presentation_v2.py`). Folie 4 = brand-konformes
      Chart als gerendertes PNG (`folie4-chart.html` → Edge headless, Anthrazit-Staffelung, Datenlabels).
      Folie 8 = „Noch Fragen?". **Status:** im visuellen Review (User prüft in PowerPoint).
- [ ] **P6 — Review-Abschluss:** offene Detailfrage Folie 4 (Logo aufs Chart-PNG?); Live-Demo proben.
- [ ] **DOC1 — PDF 1 (Methodik & Ergebnisse):** aus docs zusammenziehen, finale Tabellen (Quelle `9a72151a`).
- [ ] **DOC2 — PDF 2 (Nutzung & Ausblick):** Anleitung + Container + Limits.
- [ ] **JUDGE (optional) — `judge.py`** für `9a72151a` (blinder Qualitätsbeleg, falls Zeit).

## Definition of Done

- Präsi läuft in ≤10 min inkl. Live Demo, keine kryptischen Zahlen, jede Grafik beschriftet
  (was + Einheit + n).
- Zwei PDFs abgegeben; alle Präsi-Zahlen sind dort belegt.
- Container startet, Kollege kann nach eigenem Login die 9 synthetischen Tasks fahren.
- Keine Aussage in der Präsi, die die finalen Daten nicht tragen (v.a. „Turns/günstiger").
