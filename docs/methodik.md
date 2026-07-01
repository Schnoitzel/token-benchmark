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

### Modelluebergreifender Referenzlauf

Run `dcf6c6db` (Baseline, alle drei Modelle, je 3 Wiederholungen) zeigt, dass der
Effekt **modelluebergreifend** besteht (Rohdaten + Report versioniert unter
[`docs/evidence/`](evidence/)):

| Modell | Pi Overhead (median) | Claude Code Overhead (median) | Faktor |
|--------|---------------------:|------------------------------:|-------:|
| Haiku 4.5 | 3.070 | 29.294 | ~9,5× |
| Sonnet 4.6 | 3.069 | 28.465 | ~9,3× |
| Opus 4.8 | 3.786 | 27.256 | ~7,2× |

Streuung in allen Faellen < 0,1 % (max−min weniger als ~6 Tokens). Die Aussage
„Claude Code schickt ein Vielfaches an Overhead pro Anfrage“ ist damit robust
und nicht modellspezifisch.

### Was das bedeutet (wichtig fuer die Ehrlichkeit der Aussage)

1. **Pi-Caching ist modellabhaengig** — nicht generell abwesend:
   - **Haiku 4.5:** Pi schickt den System-Prompt bei *jeder* Anfrage als reinen
     `input` (`cache_read = cache_write = 0`). Kein server-seitiges Caching.
   - **Sonnet 4.6 und Opus 4.8:** Pi aktiviert server-seitiges Prompt-Caching.
     Run #0 (kalt): `cache_write ≈ 3.066–3.784`. Run #1+ (warm, ≤5 Min):
     `cache_read ≈ 1.870–2.504`, `cache_write ≈ 1.194–1.280`.
   - **Wichtig:** Der **Token-Overhead** ist in allen Faellen gleich
     (`input + cache_read + cache_write ≈ 3.069–3.786`) — stabil warm/kalt.
     Die **Kosten** dagegen schwanken: Pi Sonnet kalt ≈ $0.012, warm ≈ $0.005
     (Faktor ~2,3×). Fuer den Kosten-Vergleich wird deshalb der Median ueber
     ≥3 Wiederholungen empfohlen (enthaelt sowohl kalt als auch warm).

   *(Beobachtung aus Referenzlauf dcf6c6db, Rohdaten in docs/evidence/. Warum
   Haiku nicht cacht, Sonnet/Opus aber schon: moeglicherweise modellspezifische
   Cache-Schwellenwerte bei Anthropic. Nicht offiziell dokumentiert.)*

2. **Claude Code nutzt server-seitiges Prompt-Caching konsistent** ueber alle
   Modelle. Sein ~27–29k grosser Kontext teilt sich in:
   - `cache_read ≈ 20.896–21.506` (stabiler Kern, auch bei run#0 bereits
     gecacht — *Beobachtung:* moeglicherweise Anthropic-seitig persistent
     fuer CC als offiziellem Tool; nicht offiziell dokumentiert)
   - `cache_write ≈ 3.856–7.778` (dynamischer Teil, session-spezifisch)

3. **Der Token-Overhead ist unabhaengig vom Cache-Warm/Kalt-Zustand stabil.**
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

## Bekannte Einschraenkungen & offene Fragen

- **Cache-TTL fuer Claude-4-Modelle nicht explizit verifiziert.** Die Anthropic-Dokumentation
  beschreibt 5 Minuten TTL fuer claude-3-Modelle. Fuer Haiku 4.5, Sonnet 4.6, Opus 4.8
  wird dieselbe TTL angenommen — aus den Messdaten nicht direkt ableitbar (wir messen
  keinen Zeitverlauf, nur Tokens). *→ Queuelle: docs.anthropic.com/en/docs/build-with-claude/prompt-caching (Phase-F-TODO: verifizieren)*

- **Stabiler CC-Kern (cache_read ~21.500 Tokens) ist Beobachtung, nicht belegte Tatsache.**
  Dass dieser Anteil bereits beim allerersten Run gecacht ist, koennte auf Anthropic-seitiges
  Langzeit-Caching fuer Claude Code als eigenem Produkt hindeuten. Nicht offiziell dokumentiert.

- **Pi-Caching-Verhalten bei Sonnet/Opus: Ursache unklar.** Moegliche Erklaerungen:
  minimale Cache-Token-Schwelle (Haiku-SP knapp darunter), oder modellspezifische
  Anthropic-Konfiguration. Beobachtung, keine offizielle Erklaerung.

- **`medium-bash`-Task (use_tools=True): muss environment-symmetrisch sein.**
  Der urspruengliche Prompt fragte nach `/usr/share/doc` (Linux-Pfad). CC laeuft als
  Windows-Prozess und fand diesen Pfad nie zuverlaessig (CC Opus: 0/10 Erfolge,
  CC Sonnet: Overhead-Streuung 116k–396k Tokens). Der Task wurde durch eine
  environment-agnostische Systeminfo-Aufgabe ersetzt (ADR-0003, 2026-06-29).
  Lernprinzip: Tool-Tasks muessen auf environment-Symmetrie geprueft werden bevor
  Ergebnisse als Overhead-Vergleich gewertet werden.

- **Plattform-Asymmetrie: CC laeuft als Windows-Prozess, Pi nativ in Linux/WSL.**
  In der Messumgebung ist `claude` ein Windows-Binary (`/mnt/c/.../npm/claude`),
  `pi` laeuft in WSL/Linux. Das betrifft **ausschliesslich Tool-/Multi-Turn-Tasks**
  (Tokens, Turns, Laufzeit verfaelscht) — die **Overhead-Kernzahl ~8x bleibt gueltig**,
  weil sie auf Single-Turn-Tasks (`num_turns=1`, keine Tool-Ausfuehrung) beruht.
  Konkret betroffen: `medium-bash` (7–16 Turns) und leicht `simple-code` (2 Turns);
  die Real-Tasks (Repo unter `/mnt/c`, 13–20 Turns) sind ebenfalls verfaelscht — dort
  liegt Pi **nicht** durchgaengig vorne (bei Haiku teurer/langsamer als CC). Faire
  Tool-Messung erfordert gleiches OS fuer beide → **Container** (ADR-0004, 2026-06-30).

*Quellen-Vollbeleg (Phase F) steht aus. Alle Befunde bis dahin: Messdaten in*
*`docs/evidence/`, Anthropic-Docs unter https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching*
*und https://www.anthropic.com/pricing*
