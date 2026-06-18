# Token-Benchmark – Pi vs Claude Code (Python)

Misst den Token-Overhead zweier KI-Coding-Harnesses bei identischen Prompts und Modellen.

**Keine Abhängigkeiten** – läuft mit purem Python 3.10+ (nur Standardbibliothek).

## Hintergrund

Beide Harnesses nutzen dieselbe Anthropic API, setzen aber unterschiedlich viele
**System-Prompt-Tokens** ein:

| Harness | System-Prompt-Strategie |
|---------|-------------------------|
| **Pi** | Minimalistisch – nur Kern-Tools, kein Sub-Agent, kein Plan-Mode |
| **Claude Code** | Feature-reich – voller System-Prompt inkl. MCP, Permissions, Sub-Agents, … |

**Verifiziert gemessen (Haiku 4.5, Baseline, 5 Wiederholungen, Run `3997a0b9`):**
- Pi: **~3.069 Overhead-Tokens** (System-Prompt als reiner `input`, kein Caching)
- Claude Code: **~29.296 Overhead-Tokens** (`input` + `cache_read` + `cache_write`)
- → **≈ 9,5× Token-Overhead** (Kosten-Overhead ~5×, da CC viel billiges `cache_read` nutzt)

Overhead = `input + cache_read + cache_write` (Kontext pro Anfrage ohne Antwort),
bei beiden hoch reproduzierbar (Streuung < 2 Tokens). Vollstaendige Methodik und
Cache-Semantik: **[docs/methodik.md](docs/methodik.md)**.

## Voraussetzungen

- Python 3.10+
- `pi` und `claude` müssen installiert und eingeloggt sein (im PATH)

## 🖥️ Web-Oberfläche (empfohlen, auch für Nicht-Programmierer)

Einfach den Server starten – der Browser öffnet sich automatisch:

```bash
cd token-benchmark-py
python3 server.py
```

Dann im Browser (öffnet sich automatisch): **http://localhost:8000**

In der Oberfläche kannst du:
- Harnesses, Modelle und Aufgaben per Klick auswählen
- den Benchmark mit einem Button starten
- den **Fortschritt live** mitverfolgen (Fortschrittsbalken + Log)
- Ergebnisse als **Kennzahlen-Kacheln, Balkendiagramme und Tabellen** sehen
- die **Antworten beider Harnesses nebeneinander** vergleichen (Qualität)
- **frühere Läufe** wieder laden

Server beenden: `Strg+C` im Terminal.

Anderer Port: `python3 server.py --port 9000`
Ohne automatisches Browser-Öffnen: `python3 server.py --no-open`

## Schnellstart (Kommandozeile, alternativ)

```bash
cd token-benchmark-py

# Trockentest (zeigt nur, was laufen würde – kostet nichts)
python3 main.py --dry-run

# Alle Tasks, alle Modelle, beide Harnesses (48 Runs)
python3 main.py

# Nur triviale Tasks, nur Sonnet
python3 main.py --complexity trivial --models "Sonnet 4.6"

# Nur Pi, Haiku
python3 main.py --harnesses pi --models "Haiku 3.5"

# Report aus vorhandenem Ergebnis erzeugen
python3 report.py                                  # neuestes
python3 report.py results/benchmark-abcd1234.json  # bestimmtes
```

## CLI-Optionen

| Option | Standard | Beschreibung |
|--------|----------|--------------|
| `--harnesses` | `pi,claude-code` | Kommagetrennte Harnesses |
| `--models` | alle | Kommagetrennte Modell-Labels |
| `--tasks` | alle | Kommagetrennte Task-IDs |
| `--complexity` | alle | `trivial,simple,medium,complex` |
| `--delay` | `2.0` | Pause zwischen Runs (Sekunden) |
| `--dry-run` | – | Zeigt nur, was laufen würde |
| `--no-report` | – | Kein Markdown-Report nach dem Run |

## Modelle

Definiert in `models.py` – einfach editieren/ergänzen:

| Label | Pi Model-ID | CC Alias | Tier |
|-------|-------------|----------|------|
| Haiku 4.5 | `claude-haiku-4-5` | `haiku` | cheap |
| Sonnet 4.6 | `claude-sonnet-4-5` | `sonnet` | mid |
| Opus 4.8 | `claude-opus-4-8` | `opus` | expensive |

## Tasks

Definiert in `tasks.py`:

| ID | Komplexität | Tool-Use | Beschreibung |
|----|-------------|----------|--------------|
| `trivial-fact` | trivial | nein | Faktenfrage (Berliner Mauer) |
| `trivial-math` | trivial | nein | 17 × 23 |
| `simple-code` | simple | nein | TypeScript debounce-Funktion |
| `simple-explain` | simple | nein | Promise.all vs allSettled |
| `medium-design` | medium | nein | REST-API Design |
| `medium-bash` | medium | **ja** | Größte Dateien finden (bash) |
| `complex-refactor` | complex | nein | Python Code-Review + Refactor |
| `complex-analysis` | complex | nein | OLTP/OLAP Architektur-Analyse |

## Was wird gemessen?

```
Token-Kategorien (Anthropic API):
  cache_write  = System-Prompt + Tool-Definitionen (erster Aufruf)
  cache_read   = gecachte Tokens aus vorherigem Aufruf
  input        = User-Nachricht (die eigentliche Anfrage)
  output       = Antwort des Modells

Kosten-Faustregel (Anthropic):
  cache_write ~ 1,25x normal (einmalig)
  cache_read  ~ 0,1x normal   <- deutlich günstiger!
  input       = 1x normal
  output      ~ 5x normal
```

## Ergebnisse

Nach jedem Run:
- `results/benchmark-<runId>.json` – Rohdaten (alle Tokens, Kosten, Antworten)
- `results/report-<runId>.md` – formatierter Bericht mit Vergleichstabellen und vollen Antworten

## Dateistruktur

```
token-benchmark-py/
├── server.py        # Web-Server fuer die UI  <- START HIER fuer die Oberflaeche
├── static/
│   └── index.html   # die Web-Oberflaeche (HTML/CSS/JS)
├── core.py          # gemeinsame Benchmark-Logik (UI + CLI)
├── main.py          # CLI-Einstiegspunkt (Kommandozeile)
├── models.py        # Modell-Definitionen
├── tasks.py         # Task-Definitionen (Prompts)
├── runners.py       # Pi- und Claude-Code-Runner (parsen JSON-Ausgabe)
├── report.py        # Report-Generator (Markdown)
└── results/         # wird automatisch erstellt
```

## Tests

Die Test-Suite nutzt – wie das Tool selbst – **nur die Python-Standardbibliothek**
(`unittest`), keine Installation noetig.

```bash
# Alle (schnellen) Unit-Tests – mit Mocks, kostenlos, keine API-Aufrufe
python3 -m unittest discover -s tests

# Einzelnes Modul
python3 -m unittest tests.test_pricing
```

Die Unit-Tests decken die reine Logik ab (Pricing, Judge-Parsing/Swap-Test,
Report-Aggregation, Runner-Parsing gegen **echte** Beispielausgaben in
`tests/fixtures/`, Core-Orchestrierung). Sie laufen ohne `pi`/`claude` und ohne
Netz.

**Reale Messung (opt-in, kostet Tokens):** Tests, die echte Aussagen ueber den
Token-Verbrauch treffen, rufen `pi`/`claude` wirklich auf. Sie sind standardmaessig
uebersprungen und werden nur mit gesetzter Umgebungsvariable ausgefuehrt:

```bash
RUN_LIVE=1 python3 -m unittest tests.test_live_measurement
```

## Wichtiger technischer Hinweis

Pi liest im Print-Modus (`-p`) auch `stdin` und wartet auf EOF. Wird Pi als
Unterprozess mit offener stdin-Pipe gestartet, hängt es. Deshalb starten die
Runner alle Prozesse mit geschlossenem stdin (`stdin=DEVNULL`).

## Methodik

**Pi:**
```
pi -p "<prompt>" --mode json --no-session --no-context-files --thinking off --model <model>
```

**Claude Code:**
```
claude -p "<prompt>" --output-format json --model <model> --allow-dangerously-skip-permissions
```

Token-Daten kommen direkt aus den API-Antworten der jeweiligen Harnesses.
