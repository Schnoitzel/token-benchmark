# ADR-0005: Datenquellen-Merge — faire Gesamtsuite (Single-Turn Windows + Tool Container)

- **Status:** akzeptiert
- **Datum:** 2026-06-30
- **Kontext-ADR:** baut auf ADR-0004 (Plattform-Asymmetrie CC=Windows / Pi=Linux) auf.

## Kontext

Der große Referenzlauf `benchmark-d1b7ef63.json` (540 Runs, n=10) wurde mit Claude
Code als **Windows-Binary** gefahren, Pi unter Linux/WSL. Dadurch sind die Tool-/
Multi-Turn-Tasks (`medium-bash`) verfälscht (ADR-0004) — der Single-Turn-Overhead
(~6–8×) bleibt OS-unabhängig gültig.

Inzwischen wurde ein **Container** gebaut (beide Harnesses nativ Linux) und
`medium-bash` darin **fair neu gefahren**: `benchmark-c066a92f.json` (60 Runs, n=10,
0 Fehler, claude 2.1.196). Ergebnis: konsistent **4,7–6,8×** statt der Windows-
Artefakt-Werte 14–22×; CC-Streuung ×1,9 → ×1,0, CC-Turns 7–16 → 2–5.

Für Präsentation und UI wird **eine** zitierfähige 540-Run-Suite gebraucht — nicht
zwei nebeneinander.

## Entscheidung

**Option A — Merge mit ehrlicher Provenienz:**
- Aus der alten 540-Run-Suite (`d1b7ef63`) alle 60 `medium-bash`-Runs **entfernen**
  und durch die 60 fairen Container-Runs (`c066a92f`) **ersetzen**.
- Aggregate (Median/Streuung) komplett **neu berechnen** (`stats.build_aggregates`).
- Provenienz als **gemischt kennzeichnen** (`provenance.merge_provenance`): Single-
  Turn-Tasks aus dem Windows-Lauf (claude 2.1.170), `medium-bash` aus dem Linux-
  Container (claude 2.1.196), inkl. Begründung + Warnhinweis.
- Reproduzierbar über `merge_suites.py` (parametrierbar).
- Ergebnis: **`benchmark-9a72151a.json`** (540 Runs) — die zitierfähige Präsi-Quelle.
- `results/` aufgeräumt: alte `d1b7ef63` + `c066a92f` + 2 Baseline-Einzeltests
  entfernt (Backup in `/tmp/results-backup-*.tar.gz`); behalten: `9a72151a` (Quelle)
  + 7 Real-Task-JSONs.

### Verworfene Alternativen
- **Option B (zwei getrennte Quellen):** in UI/Präsi unübersichtlich, ständige
  Erklärung „welche Zahl aus welcher Datei".
- **Option C (kompletter Container-Referenzlauf, alle 540 neu):** methodisch am
  saubersten, aber teuer — die 480 Single-Turn-Runs sind OS-unabhängig, ein
  Neulauf brächte keinen inhaltlichen Mehrwert. Bleibt als spätere Option offen.

## Konsequenzen

- ➕ Eine konsistente, faire 540-Run-Suite für Präsentation und UI.
- ➕ Single-Turn-Overhead unverändert (OS-unabhängig, bleibt belastbar).
- ➕ `medium-bash` jetzt fair: 6,8× / 6,5× / 4,7× (Haiku/Sonnet/Opus).
- ➖ **Gemischte Claude-Code-Version** (2.1.170 Single-Turn / 2.1.196 Tool). Für den
  Overhead-/Token-Vergleich irrelevant (beide messen denselben Harness-Overhead),
  aber transparent dokumentiert.
- 🔭 Spätere Option C (vollständiger Container-Lauf) für 100 % Einheitlichkeit bleibt
  möglich; dann `merge_suites.py` obsolet.

## Belege

- Faire Faktoren: medium-bash neu 6,8/6,5/4,7× (c066a92f) vs. Windows-Artefakt 21,7/
  14,3/21,3× (d1b7ef63).
- Provenienz-Mix maschinenlesbar in `benchmark-9a72151a.json` →
  `provenance.merge_provenance`.
