# Methodik & Belastbarkeit der Zahlen

Dieses Dokument erklaert **wie** die Zahlen erhoben werden und **warum** sie
belastbar sind. Es ist die Referenz hinter jeder Kennzahl in Report und UI.

## Was wird gemessen?

Beide Harnesses (Pi, Claude Code) bekommen **denselben Prompt**, **dasselbe
Modell** und laufen in **identisch leerer Umgebung** (frisches temporaeres
Arbeitsverzeichnis, kein Projektkontext). Gemessen werden die Token-Zahlen
direkt aus den API-Antworten der Harnesses, aufgeteilt in:

| Feld | Bedeutung |
|------|-----------|
| `input` | nicht-gecachte Eingabe-Tokens (User-Nachricht + ggf. ungecachter System-Prompt) |
| `cache_read` | aus dem Anthropic-Prompt-Cache gelesene Tokens (guenstig, 0,10× Input-Preis) |
| `cache_write` | in den Cache geschriebene Tokens (1,25× Input-Preis) |
| `output` | vom Modell erzeugte Antwort |

**Harness-Overhead** (die zentrale Kennzahl) = `input + cache_read + cache_write`
— also der gesamte **pro Anfrage mitgeschickte Kontext ohne die Antwort**.
Bei einem Trivial-Prompt (`baseline-overhead`) ist das praktisch nur
**System-Prompt + Tool-Definitionen**, die jeder Harness bei *jeder* Anfrage
mitschickt — unabhaengig von Aufgabe und Antwortlaenge.

## Verifizierte Cache-Semantik (echte Messung)

Run `3997a0b9`, Modell **Haiku 4.5**, Task `baseline-overhead`, je 5 Wiederholungen,
beide Harnesses in leerer Sandbox:

| Harness | input | cache_read | cache_write | Overhead (median) | Streuung |
|---------|------:|-----------:|------------:|------------------:|---------:|
| **Pi** | 3.069 | 0 | 0 | **3.069** | min 3.068 / max 3.069 (σ≈0,4) |
| **Claude Code** | 10 | 21.506 | ~7.778 | **29.296** | min 29.292 / max 29.296 (σ≈1,6) |

**Faktor Overhead CC/Pi: ~9,55×.**

### Was das bedeutet (wichtig fuer die Ehrlichkeit der Aussage)

1. **Pi nutzt in dieser blank/ephemeren Konfiguration kein Prompt-Caching.**
   Der System-Prompt wird bei *jeder* Anfrage als reiner `input` geschickt
   (`cache_read = cache_write = 0`). Pi zahlt seinen Overhead also voll zum
   Input-Preis — und der ist trotzdem ~10× kleiner als der von Claude Code.

2. **Claude Code nutzt server-seitiges Prompt-Caching.** Sein ~29,3k grosser
   Kontext teilt sich in einen stabil gecachten Anteil (`cache_read ≈ 21.506`,
   ueber alle Laeufe konstant) und einen pro Anfrage neu geschriebenen Anteil
   (`cache_write ≈ 7.778`).

3. **Der Total-Overhead ist unabhaengig vom Cache-Warm/Kalt-Zustand stabil.**
   `input + cache_read + cache_write` lag in einer voellig getrennten frueheren
   Messung (Fixture, andere Sitzung) bei 29.230 und hier bei 29.296 — Differenz
   < 0,3 %. Das ist die belastbarste Form der Kennzahl: Sie misst den **gesamten
   pro Anfrage mitgeschickten Kontext**, egal wie er auf input/cache aufgeteilt ist.

### Token-Overhead ≠ Kosten-Overhead

Der Token-Overhead ist ~9,5×, der **Kosten**-Overhead aber kleiner (~5×), weil
der Grossteil von Claude Codes Overhead aus **billigem `cache_read`** besteht
(0,10× Input-Preis). Beide Zahlen sind real und werden getrennt ausgewiesen —
Tokens zeigen den Umfang, Kosten den finanziellen Effekt.

## Reproduzierbarkeit

- **Wiederholungen** (`--repeat`): Mehrere Laeufe je Kombination erlauben
  Median + Streuung statt Einzelwert. Die Baseline-Streuung ist extrem klein
  (σ < 2 Tokens), die Kernzahl damit hoch belastbar.
  - **Empfehlung / Default-Entscheidung:** Der CLI-/UI-Default bleibt bewusst
    `repeat = 1` (kostet am wenigsten, schnelle Exploration). Fuer **belastbare,
    zitierfaehige** Zahlen – v.a. die Baseline-Overhead-Kernzahl – wird
    `--repeat 5` empfohlen (so entstanden die Zahlen oben). Begruendung: Bei der
    beobachteten Mini-Streuung (rel. Streuung < 0,1 %) reichen 5 Wiederholungen
    voellig, um Median + Spanne stabil auszuweisen; mehr bringt kaum Mehrwert
    bei linear steigenden Kosten.
- **Provenienz**: Jede Suite-JSON enthaelt Versionen, Flags, Preise, Cache-Faktoren
  und Plattform (`provenance`-Block) — der Lauf ist nachvollziehbar reproduzierbar.
- **Einheitliche Kosten**: Die Kosten werden fuer *beide* Harnesses aus *einer*
  Preistabelle (`pricing.py`) und den gemessenen Tokens berechnet, nicht aus der
  Eigenangabe der Harnesses. So haengt der Kostenunterschied nachweisbar nur an
  den Tokens.

## Verwendete Flags

- **Pi:** `-p --mode json --no-session --no-context-files --no-prompt-templates --thinking off --model <id>`
- **Claude Code:** `-p --output-format json --model <id> --allow-dangerously-skip-permissions`
