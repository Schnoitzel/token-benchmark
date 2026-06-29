# Benchmark Resume-Funktion

- **Status:** Done
- **Date:** 2026-06-29
- **Branch/Worktree:** n/a

## Problem
Bei einem 540-Run-Lauf (n=10, alle Modelle/Tasks) kann der Prozess abstürzen
oder hängen bleiben (Timeout, Netzwerkfehler, Browser-Disconnect). Die bereits
abgeschlossenen Runs sind zwar sofort in der JSON gespeichert, aber beim Neustart
entsteht eine neue `run_id` → neuer Lauf von vorne. Bereits bezahlte Runs sind
verloren.

## Scope
### In scope
- `run_plan` im Suite-JSON speichern (tasks, models, harnesses, repeat, total)
- Resume-Logik in `run_benchmark_iter`: bereits erledigte Runs überspringen
- Neuer Server-Endpunkt `/api/resume?run_id=X` (rekonstruiert Plan aus JSON)
- UI: „▶ Fortsetzen"-Button bei unvollständigen Läufen
- Unit-Tests für Resume-Logik

### Out of scope
- Automatisches Resume beim Serverstart
- Merge zweier voneinander unabhängiger Runs (kein gemeinsamer `run_id`)
- CLI (`main.py`) Resume-Flag (später ergänzbar)

## Approach
Der einfachste zuverlässige Ansatz:
1. Jeder Lauf speichert `run_plan` mit den exakten Parametern
2. Resume lädt die bestehende JSON, baut ein Set erledigter
   `(task_id, model_label, harness, repeat_index)` und überspringt sie im Loop
3. Alles schreibt weiterhin in dieselbe Datei → kein Merge nötig

## Design

### Änderung `core.py`
- `run_benchmark_iter()`: neuer optionaler Parameter `resume_run_id: str | None`
- `_save()`: schreibt `run_plan` ins Suite-JSON
- Wenn `resume_run_id` gesetzt:
  - Lade bestehende JSON
  - Übernehme `run_id`, `started_at`, `out_file`, `results` aus der Datei
  - Baue `done_set`: `{(task_id, model_label, harness, repeat_index)}`
  - Überspringe Kombinationen die in `done_set` sind
  - `idx` startet bei `len(existing_results)` (für korrekten Fortschritt)

### Änderung `server.py`
- Neuer Endpunkt `GET /api/resume?run_id=X`:
  - Lädt JSON für `run_id`
  - Liest `run_plan` (tasks, models, harnesses, repeat)
  - Rekonstruiert Task- und Model-Objekte
  - Ruft `run_benchmark_iter(..., resume_run_id=run_id)` auf
  - Antwortet als SSE-Stream (identisch zu `/api/run`)
- `/api/results`: fügt `is_complete` und `total` zum Item hinzu

### Änderung `static/index.html`
- In der Ergebnisliste: bei `!item.is_complete` ein „▶ Fortsetzen"-Button
- Klick → GET `/api/resume?run_id=<id>` als SSE → normaler Progress-Flow

### Neues Format `run_plan` im Suite-JSON
```json
{
  "run_plan": {
    "task_ids": ["baseline-overhead", "trivial-fact", ...],
    "model_labels": ["Haiku 4.5", "Sonnet 4.6", "Opus 4.8"],
    "harnesses": ["pi", "claude-code"],
    "repeat": 10,
    "total": 540
  }
}
```

## Task Breakdown

- [x] Plan schreiben
- [x] `core.py`: `run_plan` in `_save()` ergänzen
- [x] `core.py`: `resume_run_id`-Parameter + Skip-Logik
- [x] `server.py`: `/api/results` → `is_complete` + `total` hinzufügen (`build_results_list`)
- [x] `server.py`: `/api/resume` Endpunkt
- [x] `static/index.html`: „▶ Fortsetzen“-Button
- [x] `tests/`: Unit-Tests für Resume-Logik (9 Tests, alle grün)
- [x] `benchmark-d1b7ef63.json`: `run_plan` manuell ergänzt (39/540 resumable)

## Test Strategy
- `tests/test_resume.py`: hermetisch, kein Netz, Mocks via `unittest.mock`
- Testfälle:
  - Resume überspringt genau die erledigten Runs
  - Resume mit leerem Done-Set (= normaler Lauf)
  - Resume mit vollständigem Done-Set (= kein Run mehr)
  - `run_plan` korrekt im JSON gespeichert
  - `is_complete` korrekt in `/api/results`
- Ausführen: `python3 -m unittest discover -s tests`

## Risks & Open Questions
- `repeat_index` im bestehenden JSON: Feld heißt `repeat_index` (int 0-9) ✅
- Echter Lauf `benchmark-d1b7ef63.json` hat kein `run_plan` → Resume-Endpunkt
  muss graceful damit umgehen (Fallback: Parameter nochmal aus UI senden)

## Definition of Done
- [ ] Tests grün: `python3 -m unittest discover -s tests`
- [ ] „▶ Fortsetzen" erscheint in der UI bei `benchmark-d1b7ef63.json`
- [ ] Klick auf Button startet Lauf ab Run 40 in dieselbe JSON
- [ ] Nach Abschluss: `finished_at` gesetzt, Button verschwindet
