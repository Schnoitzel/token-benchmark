# Token-Verbrauch Benchmark - Pi vs Claude Code

**Run-ID:** `dcf6c6db`  
**Start:** 2026-06-18T15:43:05.428413+00:00  
**Ende:** 2026-06-18T15:44:24.291803+00:00  
**Wiederholungen je Kombination:** 3 (alle Zahlen sind Mediane)  

## Kurzfassung

Dieser Benchmark misst den Token-Overhead zweier KI-Coding-Harnesses - **Pi** (minimalistisch) und **Claude Code** (funktionsreich) - bei identischen Prompts, identischen Modellen und in identisch sauberer Umgebung (leeres Arbeitsverzeichnis, kein Projektkontext).

## Baseline: reiner Harness-Overhead

Gemessen mit einem Trivial-Prompt. Die Antwort ist winzig, daher ist `Input + Cache` praktisch nur **System-Prompt + Tool-Definitionen**, die jeder Harness bei **jeder** Anfrage mitschickt - unabhaengig von Aufgabe und Antwortlaenge. Das ist die belastbarste Overhead-Kennzahl.

| Modell | Pi Overhead (Median, min–max, n) | Claude Code Overhead (Median, min–max, n) | Faktor |
|--------|-------------------------------:|----------------------------------------:|-------:|
| Haiku 4.5 | 3,070 (3,068–3,071, n=3) | 29,294 (29,294–29,296, n=3) | **9.5x** |
| Sonnet 4.6 | 3,069 (3,067–3,069, n=3) | 28,465 (28,463–28,469, n=3) | **9.3x** |
| Opus 4.8 | 3,786 (3,786–3,786, n=3) | 27,256 (27,256–27,256, n=3) | **7.2x** |

_Belastbarkeit: groesste relative Streuung in diesem Block **0.1%** (Spanne/Median). Faustregel: < 5 % = sehr stabil, die Kernzahl ist dann hoch belastbar. Mehr Wiederholungen (`--repeat`) verkleinern die Streuung._

## System-Prompt-Overhead je Modell

Median der `Input + Cache`-Tokens (= mitgeschickter Kontext ohne Antwort).

| Modell | Pi | Claude Code | Faktor |
|--------|---:|------------:|-------:|
| Haiku 4.5 | 3,070 | 29,294 | **9.5x** |
| Sonnet 4.6 | 3,069 | 28,465 | **9.3x** |
| Opus 4.8 | 3,786 | 27,256 | **7.2x** |

## Ergebnisse pro Task & Modell

Aggregiert ueber 3 Wiederholung(en): **Median**, in Klammern **min-max** bei Total & Kosten.

### baseline-overhead

- **Komplexitaet:** baseline

| Modell | Harness | n | Input | Output | Cache R | Cache W | Total (min-max) | Kosten (min-max) | Dauer |
|--------|---------|--:|------:|-------:|--------:|--------:|----------------:|-----------------:|------:|
| Haiku 4.5 | claude-code | 3 | 10 | 43 | 21,506 | 7,778 | 29,337 (29,330-29,423) | $0.01210 ($0.01206-$0.01252) | 3.6s |
| Haiku 4.5 | pi | 3 | 3,070 | 4 | 0 | 0 | 3,074 (3,072-3,075) | $0.00309 ($0.00309-$0.00309) | 1.9s |
| Opus 4.8 | claude-code | 3 | 2,504 | 4 | 20,896 | 3,856 | 27,260 (27,260-27,260) | $0.14150 ($0.14150-$0.14150) | 4.0s |
| Opus 4.8 | pi | 3 | 2 | 4 | 2,504 | 1,280 | 3,790 (3,790-3,790) | $0.02809 ($0.02809-$0.07128) | 2.8s |
| Sonnet 4.6 | claude-code | 3 | 3 | 4 | 20,861 | 7,601 | 28,469 (28,467-28,473) | $0.03483 ($0.03482-$0.03485) | 4.3s |
| Sonnet 4.6 | pi | 3 | 3 | 4 | 1,870 | 1,196 | 3,073 (3,071-3,073) | $0.00511 ($0.00511-$0.01157) | 2.5s |

## Antworten

_Je Kombination eine repraesentative Antwort (erste Wiederholung) zur qualitativen Bewertung._

### baseline-overhead - Antworten

**Prompt:**

```
Reply with exactly: OK
```

#### Haiku 4.5

**claude-code** (29,330 Tokens, $0.01206):

OK

**pi** (3,074 Tokens, $0.00309):

OK

#### Sonnet 4.6

**claude-code** (28,473 Tokens, $0.03485):

OK

**pi** (3,073 Tokens, $0.01157):

OK

#### Opus 4.8

**claude-code** (27,260 Tokens, $0.14150):

OK

**pi** (3,790 Tokens, $0.07128):

OK

## Methodik & Provenienz

- **Pi-Version:** `0.79.6`
- **Claude-Code-Version:** `2.1.170 (Claude Code)`
- **Pi-Flags:** `-p --mode json --no-session --no-context-files --no-prompt-templates --thinking off --model <id>`
- **Claude-Code-Flags:** `-p --output-format json --model <id> --allow-dangerously-skip-permissions`
- **Umgebung:** leeres temporaeres Arbeitsverzeichnis pro Lauf (kein Projektkontext)
- **Wiederholungen:** 3
- **Kostenbasis:** einheitlich aus Token-Zahlen berechnet (pricing.py), nicht aus Harness-Eigenangabe
- **Preise:** Haiku 4.5: in $1.0/MTok · out $5.0/MTok, Sonnet 4.6: in $3.0/MTok · out $15.0/MTok, Opus 4.8: in $15.0/MTok · out $75.0/MTok
- **Cache-Faktoren:** write ×1.25 · read ×0.1 (relativ zum Input-Preis)
- **Plattform:** Linux-5.15.133.1-microsoft-standard-WSL2-x86_64-with-glibc2.35 · Python 3.10.12
- Token-Zahlen stammen direkt aus den API-Antworten der Harnesses.
- Overhead = `input + cache_read + cache_write` (mitgeschickter Kontext ohne Antwort).
- Pi schickt den System-Prompt als reinen `input` (kein Caching); Claude Code nutzt server-seitiges Prompt-Caching (`cache_read` + `cache_write`). Der Total-Overhead ist warm/kalt-unabhaengig stabil – Details: `docs/methodik.md`.
- Kosten werden fuer **beide** Harnesses einheitlich aus den Token-Zahlen berechnet (pricing.py).