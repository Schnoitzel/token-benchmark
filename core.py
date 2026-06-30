"""
core.py - wiederverwendbare Benchmark-Logik.

Wird sowohl von main.py (Kommandozeile) als auch von server.py (Web-UI) genutzt.

run_benchmark_iter() ist ein Generator: er liefert nach und nach Ereignisse
(Fortschritt, Einzelergebnis, Abschluss), sodass die UI live mitlesen kann.
"""

import json
import os
import platform
import sys
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Iterator

import pricing
import stats
from models import MODELS, Model
from tasks import TASKS, Task
from runners import (
    CC_FLAGS,
    PI_FLAGS,
    RunResult,
    TokenUsage,
    get_tool_versions,
    run_claude,
    run_pi,
)


def apply_unified_cost(res: RunResult) -> None:
    """Ueberschreibt die Kosten mit der einheitlichen Berechnung aus pricing.py.
    Der vom Harness gemeldete Wert bleibt zur Transparenz in cost_harness_usd."""
    res.usage.cost_harness_usd = res.usage.cost_usd
    unified = pricing.cost_for_usage(res.model_label, res.usage)
    if unified is not None:
        res.usage.cost_usd = unified


def build_provenance(repeat: int) -> dict:
    """Sammelt alle Angaben, die den Lauf reproduzierbar machen."""
    return {
        "tool_versions": get_tool_versions(),
        "flags": {"pi": PI_FLAGS, "claude": CC_FLAGS},
        "sandbox": "leeres temporaeres Arbeitsverzeichnis pro Lauf (kein Projektkontext)",
        "repeat": repeat,
        "pricing_usd_per_mtok": {k: {"input": v[0], "output": v[1]} for k, v in pricing.PRICES.items()},
        "cache_multipliers": {"write": pricing.CACHE_WRITE_MULT, "read": pricing.CACHE_READ_MULT},
        "cost_basis": "einheitlich aus Token-Zahlen berechnet (pricing.py), nicht aus Harness-Eigenangabe",
        "platform": platform.platform(),
        "python": sys.version.split()[0],
    }


def filter_models(only_models: list[str] | None) -> list[Model]:
    models = list(MODELS)
    if only_models:
        models = [m for m in models if m.label in only_models or m.pi_model in only_models]
    return models


def filter_tasks(
    only_tasks: list[str] | None,
    complexity: list[str] | None,
) -> list[Task]:
    tasks = list(TASKS)
    if complexity:
        tasks = [t for t in tasks if t.complexity in complexity]
    if only_tasks:
        tasks = [t for t in tasks if t.id in only_tasks]
    return tasks


def run_benchmark_iter(
    harnesses: list[str],
    models: list[Model],
    tasks: list[Task],
    delay: float = 2.0,
    repeat: int = 1,
    resume_run_id: str | None = None,
) -> Iterator[dict]:
    """
    Fuehrt den Benchmark aus und liefert Ereignisse als dicts:

      {"type": "start", "run_id", "total", "tasks", "models", "harnesses", "repeat"}
      {"type": "run_start", "index", "total", "harness", "model", "task", "repeat", "repeats"}
      {"type": "result", "index", "total", "result": {...}}
      {"type": "done", "run_id", "out_file", "suite": {...}}

    repeat: Anzahl der Wiederholungen pro (Task x Modell x Harness). Mehrere
    Wiederholungen erlauben Median/Streuung statt Einzelwert -> belastbar.

    resume_run_id: Wenn gesetzt, wird ein unterbrochener Lauf fortgesetzt.
    Bereits erledigte (task_id, model_label, harness, repeat_index)-Kombinationen
    werden uebersprungen. Der Lauf schreibt in dieselbe Datei.
    """
    repeat = max(1, int(repeat))
    total = len(tasks) * len(models) * len(harnesses) * repeat

    # run_plan wird im Suite-JSON gespeichert, damit Resume die Parameter kennt.
    run_plan = {
        "task_ids": [t.id for t in tasks],
        "model_labels": [m.label for m in models],
        "harnesses": harnesses,
        "repeat": repeat,
        "total": total,
    }

    # --- Resume-Logik ---
    # Beim Resume: bestehende Ergebnisse laden und erledigte Kombis ueberspringen.
    existing_results: list[RunResult] = []
    done_set: set[tuple] = set()

    if resume_run_id:
        out_file = f"results/benchmark-{resume_run_id}.json"
        run_id = resume_run_id
        try:
            with open(out_file, encoding="utf-8") as f:
                existing_suite = json.load(f)
            started_at = existing_suite.get("started_at",
                                            datetime.now(timezone.utc).isoformat())
            for r in existing_suite.get("results", []):
                done_set.add((
                    r.get("task_id"), r.get("model_label"),
                    r.get("harness"), r.get("repeat_index"),
                ))
                # Bestehende Results als Rohdict behalten (kein RunResult-Parsing noetig)
            existing_results = existing_suite.get("results", [])
        except (FileNotFoundError, json.JSONDecodeError):
            # Datei fehlt oder kaputt -> normaler Neustart mit gleicher run_id
            started_at = datetime.now(timezone.utc).isoformat()
    else:
        run_id = uuid.uuid4().hex[:8]
        started_at = datetime.now(timezone.utc).isoformat()
        out_file = f"results/benchmark-{run_id}.json"

    yield {
        "type": "start",
        "run_id": run_id,
        "total": total,
        "tasks": [t.id for t in tasks],
        "models": [m.label for m in models],
        "harnesses": harnesses,
        "repeat": repeat,
    }

    # results haelt ALLE Ergebnisse (bestehende + neue).
    # Beim Speichern werden immer alle zusammen geschrieben.
    all_result_dicts: list[dict] = list(existing_results)
    new_results: list[RunResult] = []
    idx = len(existing_results)  # Fortschritts-Index startet nach bestehenden Runs
    os.makedirs("results", exist_ok=True)

    def _save(finished: bool) -> dict:
        """Schreibt den aktuellen Stand atomar auf Disk.

        Strategie: erst in <out_file>.tmp schreiben, dann per os.replace()
        atomar umbenennen.  os.replace() ist auf Linux atomar (gleiche
        Partition) -- die alte Datei bleibt bis zur letzten Millisekunde
        vollstaendig lesbar.  Kein Datenverlust bei Absturz oder SIGKILL.
        """
        current_dicts = all_result_dicts + [asdict(r) for r in new_results]
        suite = {
            "run_id": run_id,
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat() if finished else None,
            "run_plan": run_plan,
            "provenance": build_provenance(repeat),
            "results": current_dicts,
            "aggregates": stats.build_aggregates(current_dicts),
        }
        tmp_file = out_file + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(suite, f, indent=2, ensure_ascii=False)
        os.replace(tmp_file, out_file)  # atomar: alte Datei bleibt bis hierher intakt
        return suite

    for task in tasks:
        for model in models:
            for harness in harnesses:
                for rep in range(repeat):
                    # Bereits erledigte Kombination ueberspringen (Resume)
                    if (task.id, model.label, harness, rep) in done_set:
                        continue

                    idx += 1
                    yield {
                        "type": "run_start",
                        "index": idx,
                        "total": total,
                        "harness": harness,
                        "model": model.label,
                        "task": task.id,
                        "repeat": rep + 1,
                        "repeats": repeat,
                    }

                    # Repo vor jedem Run zuruecksetzen (real-Tasks aendern Dateien).
                    # Ohne Reset laeuft Run 2 auf bereits gepatchtem Repo -> ungueltig.
                    if task.repo_dir and os.path.isdir(task.repo_dir):
                        import subprocess as _sp
                        _sp.run(
                            ["git", "restore", "."],
                            cwd=task.repo_dir,
                            stdout=_sp.DEVNULL,
                            stderr=_sp.DEVNULL,
                        )

                    try:
                        if harness == "pi":
                            res = run_pi(task, model)
                        else:
                            res = run_claude(task, model)
                    except Exception as e:  # noqa: BLE001
                        res = RunResult(
                            harness=harness,
                            model_label=model.label,
                            task_id=task.id,
                            task_complexity=task.complexity,
                            task_prompt=task.prompt,
                            duration_ms=0,
                            usage=TokenUsage(),
                            response="",
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            error=str(e),
                        )

                    res.repeat_index = rep
                    apply_unified_cost(res)
                    new_results.append(res)

                    # Sofort speichern - unabhaengig ob SSE-Verbindung noch steht
                    finished_now = (idx == total) or (
                        len(all_result_dicts) + len(new_results) == total
                    )
                    _save(finished=finished_now)

                    yield {
                        "type": "result",
                        "index": idx,
                        "total": total,
                        "result": asdict(res),
                    }

                    if idx < total:
                        time.sleep(delay)

    suite = _save(finished=True)
    yield {"type": "done", "run_id": run_id, "out_file": out_file, "suite": suite}
