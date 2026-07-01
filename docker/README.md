# Token-Benchmark – Container-Setup

Dieses Setup ermöglicht es, **beide Harnesses (Pi und Claude Code) unter demselben 
Betriebssystem (Linux)** zu messen – für faire Tool-/Multi-Turn-Vergleiche.

Zusätzlich dient der Container der einfachen Distribution an Kollegen, da jeder 
nur Docker braucht und sich selbst einloggt (OAuth).

## Voraussetzungen

- Docker installiert und laufend
- OAuth-Zugang zu Anthropic (kein API-Key-Login – das Tool nutzt ausschließlich OAuth)
- Für Kollegen: eigenes Anthropic-Abo-Login (jeder loggt sich selbst ein)

## Schnellstart

```bash
# 1. Image bauen (einmalig)
docker build -t token-benchmark .

# 2. OAuth-Login durchführen (einmalig, dann persistent)
# Einfachster Weg: Host-Login importieren
./docker/run.sh import-creds

# 3. UI starten
./docker/run.sh ui
# -> Öffne http://localhost:8000 im Browser

# 4. Oder: Benchmark per CLI fahren
./docker/run.sh bench --tasks medium-bash --repeat 10
```

## Befehle im Detail

### 1. Image bauen

```bash
docker build -t token-benchmark .
```

Baut das Image mit:
- Node 24 (für Pi + Claude Code)
- Python 3 (keine pip-Abhängigkeiten – reine Standardbibliothek)
- Pi + Claude Code global installiert (`npm install -g`)
- Projektcode in `/app`

### 2. OAuth-Login

**Zwei Wege stehen zur Verfügung:**

#### Weg A: Host-Credentials importieren (empfohlen)

```bash
./docker/run.sh import-creds
```

**Voraussetzung:** Pi und/oder Claude Code müssen **auf dem Host bereits eingeloggt** sein:
- **Pi:** Starte `pi` im Host-Terminal, gib im TUI den Befehl `/login` ein und folge den Anweisungen.
- **Claude Code:** Führe `claude auth login` im Host-Terminal aus und folge dem Browser-Flow.

Der Import-Befehl kopiert dann die vorhandenen Credentials (`~/.pi/agent/` und `~/.claude/`) 
ins Docker-Volume `tokenbench-creds`, wo sie persistent bleiben.

**Verifizieren:**
```bash
./docker/run.sh shell
# Im Container:
pi -p "sage OK" --mode json --no-session --no-context-files --thinking off --model claude-haiku-4-5
claude auth status
```

Beide Befehle sollten erfolgreich durchlaufen (Pi gibt eine Modell-Antwort, Claude zeigt "Logged in").

#### Weg B: Interaktiver Login im Container (umständlich)

```bash
./docker/run.sh login
```

Führt nacheinander **Pi** (interaktiver TUI mit `/login`-Befehl) und **Claude Code** 
(`claude auth login`, zeigt Device-Code/Link) im Container aus. Der OAuth-Flow erfordert 
einen **Browser auf dem Host** (Links/Codes manuell öffnen/eingeben).

**Wichtig:** Dieser Weg ist headless-unfreundlich und fehleranfällig. **Weg A wird empfohlen.**

### 3. UI starten

```bash
./docker/run.sh ui
```

Startet den Web-Server auf **http://localhost:8000**. Die UI ist identisch zur 
Host-Version (siehe Hauptdoku), mit folgenden Einschränkungen:
- **Real-Tasks (`repo_dir`) werden automatisch übersprungen**, da das JavaFX-Repo 
  nicht im Container verfügbar/teilbar ist. Wird im UI als Fehler angezeigt.
- **Results-Verzeichnis** wird vom Host gemountet (`./results:/app/results`) → 
  Ergebnisse landen auf dem Host und bleiben nach Container-Stopp erhalten.

### 4. Benchmark per CLI fahren

```bash
# Standard: medium-bash, n=10, alle Modelle
./docker/run.sh bench

# Eigene Parameter übergeben
./docker/run.sh bench --tasks simple-code --repeat 5
./docker/run.sh bench --complexity baseline --repeat 10
./docker/run.sh bench --models "Sonnet 4.6" --tasks medium-bash --repeat 10
```

Alle Argumente werden an `python3 main.py` durchgereicht. Die Suite-JSON landet 
in `./results/` auf dem Host.

### 5. Shell (Debugging)

```bash
./docker/run.sh shell
```

Startet eine interaktive Bash im Container (mit gemountetem Credentials-Volume 
und Results-Verzeichnis). Nützlich zum Debuggen.

## Wichtige Einschränkungen

| Was | Einschränkung |
|-----|---------------|
| **Real-Tasks** | Werden **übersprungen** (JavaFX-Repo nicht im Container verfügbar). Das ist gewollt – Real-Tasks sind ein Einzelszenario mit Plattform-Asymmetrie (siehe ADR-0004) und nicht Teil der Container-Messungen. |
| **OAuth-Login** | **Empfohlen:** Host-Credentials importieren (`./docker/run.sh import-creds`). Interaktiver Container-Login (`./docker/run.sh login`) ist möglich, aber headless-unfreundlich (Browser-Links/-Codes manuell handhaben). |
| **Disk-Space** | Node + Pi + Claude Code = ~250 MB Image; npm-Cache ~100 MB. Plan: ca. 400 MB gesamt. |

## Warum Container?

**Kernproblem (ADR-0004):** In der WSL-Umgebung lief `pi` als Linux-Prozess, 
`claude` aber als Windows-Prozess (über `/mnt/c/...` im PATH). Das führte bei 
**allen Tool-/Multi-Turn-Tasks** zu verfälschten Vergleichen (unterschiedliche 
Shell-Umgebungen, CRLF/LF, WSL↔Windows-Brücke).

**Lösung:** Beide Harnesses laufen **im selben Container** unter Linux → faire 
Messung des agentischen Verhaltens bei Tool-Aufgaben.

**Ergebnis:** Die Single-Turn-Overhead-Kernzahl (~8×) bleibt unverändert (ADR-0004), 
aber Tool-Tasks wie `medium-bash` sind jetzt erst zitierfähig.

## Technische Details

### Nicht-root-User
Der Container läuft als User `node` (UID 1000, standard im `node:24-bookworm-slim` Image). 
**Grund:** Claude Code verweigert `--allow-dangerously-skip-permissions` bei root aus 
Sicherheitsgründen. Credentials liegen daher in `/home/node/` (nicht `/root/`).

## Nächste Schritte nach Container-Setup

1. **`medium-bash` neu fahren** (n=10, alle Modelle, beide Harnesses im Container):
   ```bash
   ./docker/run.sh bench --tasks medium-bash --repeat 10
   ```
2. **Aggregierte Zahlen prüfen** (Median/Streuung) → diese ersetzen die Host-Zahlen
3. **Präsentation/Doku finalisieren** (siehe `docs/plans/2026-06-30-praesentation-und-doku.md`)

## Fragen / Probleme?

Bei technischen Fragen siehe:
- Haupt-README (eine Ebene höher)
- `docs/methodik.md` (Erhebungsmethode)
- `docs/adr/` (Architektur-Entscheidungen, insb. ADR-0004 zur Plattform-Asymmetrie)
