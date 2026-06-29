# Qualitätsbewertung: Real-Task „real-javafx-ui-fixes"
**Datum:** 2026-06-25  
**Richter:** Nutzer (visuell, App gebaut & gestartet)  
**Repo:** `tokentestbranch` von `/mnt/c/daten/datensicherung`  
**Methode:** Pro Harness ein Run, danach App gebaut (`mvn package`), UI visuell geprüft, dann `git restore .`

---

## Aufgabe (4 UI-Bugs)

| # | Bug | Betroffene Datei |
|---|-----|-----------------|
| 1 | Verbindungseinstellungs-Fenster nicht größenverstellbar | `ServerSettingsPane.java` |
| 2 | Zurück-Button ohne Padding im Datenwiederherstellungs-Detail | `RestoreAdvancedView.java` |
| 3 | Uhrzeit nicht immer zweistellig in den Job-Einstellungen | `TimeField.java` |
| 4 | Keine fixen Abstände in der Jobübersicht (kein tabellarischer Look) | `BackupListCell.java` |

---

## Run 1 — Pi · Haiku 4.5

> ⚠️ Erster Run (input=1, total=28.510) war fehlerhaft — Parser-Bug (nur letzter Turn).
> Zahlen unten stammen aus dem korrigierten Re-Run (alle Turns summiert).

**Token-Nutzung:**
| Feld | Wert |
|------|------|
| input | 3.762 |
| cache_write | 31.305 |
| cache_read | 590.434 |
| output | 5.207 |
| **total** | **630.708** |
| Kosten | $0.1280 |
| Dauer | 78,9 s |

**Was Pi im Code geändert hat (git diff):**

| Bug | Code-Änderung | Korrekt? |
|-----|--------------|----------|
| 1 – resizable | `setResizable(false)` → `setResizable(true)` | ✅ ja |
| 2 – padding | `backButton.setPadding(new Insets(8))` hinzugefügt | ✅ ja (Code) |
| 3 – zweistellig | Listener: `String.format("%02d", ...)` für hour/minute/second | ⚠️ teilweise |
| 4 – Spaltenbreiten | `setPrefWidth()` auf successBoxPane, infoBox, dateBox, durationBox, statsBox | ⚠️ teilweise |

**Visuelle Bewertung durch Nutzer:**

| Bug | Ergebnis | Anmerkung |
|-----|---------|-----------|
| 1 – resizable | ✅ | funktioniert |
| 2 – padding | ❌ | kein sichtbarer Effekt |
| 3 – zweistellig | ⚠️ teilweise | Listener korrekt; manuelles Eintippen einstellig weiterhin möglich |
| 4 – tabellarisch | ⚠️ teilweise | Spalten vorhanden, Text abgeschnitten, nicht aligned, Scrollbar |

**Gesamtbewertung Pi / Haiku:** 1 von 4 Bugs vollständig behoben · 2 teilweise · 1 ohne sichtbaren Effekt

**Seiteneffekte:** ⚠️ ~156 Dateien CRLF→LF konvertiert

---

## Run 2 — Pi · Sonnet 4.6

> ⚠️ Erster Run (input=1, total=24.523) war fehlerhaft — Parser-Bug. Zahlen unten aus korrigiertem Re-Run.

**Token-Nutzung:**
| Feld | Wert |
|------|------|
| input | 15 |
| cache_write | 24.775 |
| cache_read | 195.506 |
| output | 2.564 |
| **total** | **222.860** |
| Kosten | $0.1901 |
| Dauer | 56,0 s |

**Was Sonnet im Code geändert hat (git diff):**

| Bug | Code-Änderung | Korrekt? |
|-----|--------------|----------|
| 1 – resizable | `setResizable(false)` → `setResizable(true)` | ✅ ja (Code) |
| 2 – padding | `backButton.setPadding(new Insets(8))` hinzugefügt | ✅ ja (Code) |
| 3 – zweistellig | Listener: `String.format("%02d", ...)` für hour/minute/second | ⚠️ teilweise |
| 4 – Spaltenbreiten | `setPrefWidth()` auf infoBox, dateBox, durationBox, statsBox | ⚠️ teilweise |

**Visuelle Bewertung durch Nutzer:**

| Bug | Ergebnis | Anmerkung |
|-----|---------|----------|
| 1 – resizable | ❌ | Code korrekt, aber visuell kein Effekt — nicht-deterministisch (erster Run zeigte ✅) |
| 2 – padding | ❌ | kein sichtbarer Effekt |
| 3 – zweistellig | ⚠️ teilweise | Listener korrekt; manuelles Eintippen einstellig weiterhin möglich |
| 4 – tabellarisch | ⚠️ teilweise | Text abgeschnitten, nicht aligned, Scrollbar |

**Gesamtbewertung Pi / Sonnet:** 0 von 4 Bugs vollständig behoben · 2 teilweise · 2 ohne sichtbaren Effekt

**Seiteneffekte:** ⚠️ Nicht-deterministisch — im Re-Run CRLF→LF in mehreren Dateien (erster Run war sauber)
---

## Run 3 — Pi · Opus 4.8

**Token-Nutzung:** *(JSON nicht gespeichert – Run lief während Server-Neustart)*

**Was Opus im Code geändert hat (git diff):**

| Bug | Code-Änderung | Unterschied zu Haiku/Sonnet |
|-----|--------------|-----------------------------|
| 1 – resizable | `setResizable(true)` | identisch |
| 2 – padding | `backButton.setPadding(new Insets(8))` | identisch (aber Datei komplett mit LF neu geschrieben) |
| 3 – zweistellig | `String.format("%02d", ...)` im Listener | identisch |
| 4 – Spaltenbreiten | `setPrefWidth()` **+ `setMinWidth()` + `setMaxWidth()`** | ✅ vollständiger — Haiku/Sonnet nur setPrefWidth |

**Visuelle Bewertung durch Nutzer:**

| Bug | Ergebnis | Anmerkung |
|-----|---------|----------|
| 1 – resizable | ✅ | funktioniert |
| 2 – padding | ❌ | kein sichtbarer Effekt |
| 3 – zweistellig | ⚠️ teilweise | Listener korrekt; manuelle Eingabe weiterhin einstellig möglich |
| 4 – tabellarisch | ⚠️ teilweise | Text immer noch abgeschnitten trotz Min/Max/Pref |

**Gesamtbewertung Pi / Opus:** 1 von 4 Bugs vollständig behoben · 2 teilweise · 1 ohne sichtbaren Effekt

**Warum Bug 1 bei Opus sichtbar, bei Haiku/Sonnet nicht?**  
Der Code-Fix (`setResizable(true)`) war bei allen 3 identisch. Bei Haiku/Sonnet wurde die App möglicherweise nicht neu gebaut vor dem Test — beim Opus-Run wurde neu gebaut, daher war der Effekt sichtbar.

**Seiteneffekte:** `RestoreAdvancedView.java` komplett mit LF-Zeilenenden neu geschrieben (1 Datei, nicht 156 wie bei Haiku).

---

## Run 4 — Claude Code · Haiku 4.5

**Token-Nutzung:**
| Feld | Wert |
|------|------|
| input | 106 |
| cache_write | 25.119 |
| cache_read | 573.640 |
| output | 6.129 |
| **total** | **604.994** |
| Kosten | $0.1195 |
| Dauer | 61,4 s |
| Turns | 19 |

**Visuelle Bewertung durch Nutzer:**

| Bug | Ergebnis | Anmerkung |
|-----|---------|----------|
| 1 – resizable | ❌ | kein sichtbarer Effekt (Code korrekt, aber visuell nicht resizable) |
| 2 – padding | ❌ | kein sichtbarer Effekt |
| 3 – zweistellig | ⚠️ teilweise | Listener korrekt; manuelles Eintippen einstellig weiterhin möglich |
| 4 – tabellarisch | ⚠️ teilweise | Text abgeschnitten, nicht aligned |

**Gesamtbewertung CC / Haiku:** 0 von 4 Bugs vollständig behoben · 2 teilweise · 2 ohne sichtbaren Effekt

**Seiteneffekte:** keine CRLF-Konvertierung (sauber)

---

## Run 5 — Claude Code · Sonnet 4.6

**Token-Nutzung:**
| Feld | Wert |
|------|------|
| **total** | **212.766** |
| Kosten | $0.2187 |
| Dauer | 137,5 s |
| Turns | 13 |

**Visuelle Bewertung durch Nutzer:**

| Bug | Ergebnis | Anmerkung |
|-----|---------|----------|
| 1 – resizable | ❌ | kein sichtbarer Effekt |
| 2 – padding | ❌ | kein sichtbarer Effekt |
| 3 – zweistellig | ⚠️ teilweise | |
| 4 – tabellarisch | ⚠️ teilweise | |

**Gesamtbewertung CC / Sonnet:** 0 von 4 Bugs vollständig behoben · 2 teilweise · 2 ohne sichtbaren Effekt

---

## Run 6 — Claude Code · Opus 4.8

**Token-Nutzung:**
| Feld | Wert |
|------|------|
| input | 4.123 |
| cache_write | 59.272 |
| cache_read | 667.393 |
| output | 5.468 |
| **total** | **736.256** |
| Kosten | $2.5844 |
| Dauer | 96,6 s |
| Turns | 20 |

**Visuelle Bewertung durch Nutzer:**

| Bug | Ergebnis | Anmerkung |
|-----|---------|----------|
| 1 – resizable | ❌ | kein sichtbarer Effekt |
| 2 – padding | ❌ | kein sichtbarer Effekt |
| 3 – zweistellig | ⚠️ teilweise | Listener korrekt; manuelles Eintippen einstellig weiterhin möglich |
| 4 – tabellarisch | ⚠️ teilweise | |

**Gesamtbewertung CC / Opus:** 0 von 4 Bugs vollständig behoben · 2 teilweise · 2 ohne sichtbaren Effekt

---

## Beobachtungen & Analyse

### Bug 4 (Jobübersicht tabellarisch) — strukturelles Problem
Alle Modelle wenden denselben naiven Fix an: feste `setPrefWidth()`-Werte auf den VBoxen.
Das versagt aus mehreren Gründen:
- `VBox.setVgrow(infoBox, Priority.ALWAYS)` ist weiterhin gesetzt und überstimmt `setMaxWidth()` je nach verfügbarem Platz
- Die Summe der fixen Breiten übersteigt auf kleineren Fenstern die Listenbreite → horizontale Scrollbar
- `Text`-Nodes haben kein automatisches Ellipsis → Text wird hart abgeschnitten
- Keine echte Spaltenausrichtung über Zeilen hinweg (HBox garantiert das nicht)

Ein korrekter Fix würde erfordern:
- `VBox.setVgrow(..., NEVER)` statt `ALWAYS`
- Breiten relativ zur ListView binden statt fix
- `Text` → `Label` mit `setTextOverrun(ELLIPSIS)`
- Oder kompletten Umbau auf `GridPane` mit `ColumnConstraints`

**Fazit:** Aufgabe erfordert Verständnis des JavaFX-Layout-Systems, nicht nur "füge eine Property hinzu". Kein Modell erkennt das.

### Bug 2 (Zurück-Button Padding) — möglicherweise kein visueller Effekt
`backButton.setPadding(new Insets(8))` ist technisch korrekt. Der fehlende sichtbare Effekt könnte bedeuten dass der Button bereits durch das AtlantaFX-Theme-Styling Padding erhält und `setPadding()` überschrieben wird, oder dass 8px bei diesem Button-Stil nicht sichtbar genug ist.

### Seiteneffekte Zeilenenden (CRLF → LF)
Das Repo verwendet Windows-Zeilenenden (CRLF). Pi-Modelle konvertieren Dateien beim Lesen/Schreiben auf LF:
- Haiku: 156 Dateien betroffen (massiv)
- Sonnet: 0 Dateien (sauber)
- Opus: 1 Datei betroffen (RestoreAdvancedView.java)

Das ist ein erheblicher Qualitätsunterschied — chirurgische Fixes sollten keine projektweiten Nebeneffekte erzeugen.

---

## Zusammenfassung (wird laufend ergänzt)

| Harness | Modell | Bug 1 | Bug 2 | Bug 3 | Bug 4 | Seiteneffekte |
|---------|--------|-------|-------|-------|-------|---------------|
| Pi | Haiku 4.5 | ✅ | ❌ | ⚠️ | ⚠️ | ⚠️ ~156 Dateien CRLF→LF |
| Pi | Sonnet 4.6 | ❌ | ❌ | ⚠️ | ⚠️ | ⚠️ nicht-deterministisch (Re-Run: CRLF in mehreren Dateien) |
| Pi | Opus 4.8 | ✅ | ❌ | ⚠️ | ⚠️ | ⚠️ 1 Datei LF neu geschrieben |
| Claude Code | Haiku 4.5 | ❌ | ❌ | ⚠️ | ⚠️ | keine |
| Claude Code | Sonnet 4.6 | ❌ | ❌ | ⚠️ | ⚠️ | |
| Claude Code | Opus 4.8 | ❌ | ❌ | ⚠️ | ⚠️ | keine |

---

## Token-, Kosten- & Zeitvergleich (wird laufend ergänzt)

| Harness | Modell | Total Tokens | Kosten | Dauer |
|---------|--------|-------------|--------|-------|
| Pi | Haiku 4.5 | 630.708 | $0.1280 | 78,9s |
| Pi | Sonnet 4.6 | 222.860 | $0.1901 | 56,0s |
| Pi | Opus 4.8 | 246.103 | $1.2215 | 84,7s |
| Claude Code | Haiku 4.5 | 604.994 | $0.1195 | 61,4s |
| Claude Code | Sonnet 4.6 | 212.766 | $0.2187 | 137,5s |
| Claude Code | Opus 4.8 | 736.256 | $2.5844 | 96,6s |
