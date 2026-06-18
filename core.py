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
) -> Iterator[dict]:
    """
    Fuehrt den Benchmark aus und liefert Ereignisse als dicts:

      {"type": "start", "run_id", "total", "tasks", "models", "harnesses", "repeat"}
      {"type": "run_start", "index", "total", "harness", "model", "task", "repeat", "repeats"}
      {"type": "result", "index", "total", "result": {...}}
      {"type": "done", "run_id", "out_file", "suite": {...}}

    repeat: Anzahl der Wiederholungen pro (Task x Modell x Harness). Mehrere
    Wiederholungen erlauben Median/Streuung statt Einzelwert -> belastbar.
    """
    repeat = max(1, int(repeat))
    run_id = uuid.uuid4().hex[:8]
    started_at = datetime.now(timezone.utc).isoformat()
    total = len(tasks) * len(models) * len(harnesses) * repeat

    yield {
        "type": "start",
        "run_id": run_id,
        "total": total,
        "tasks": [t.id for t in tasks],
        "models": [m.label for m in models],
        "harnesses": harnesses,
        "repeat": repeat,
    }

    results: list[RunResult] = []
    idx = 0

    for task in tasks:
        for model in models:
            for harness in harnesses:
                for rep in range(repeat):
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
                    results.append(res)
                    yield {
                        "type": "result",
                        "index": idx,
                        "total": total,
                        "result": asdict(res),
                    }

                    if idx < total:
                        time.sleep(delay)

    finished_at = datetime.now(timezone.utc).isoformat()
    suite = {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "provenance": build_provenance(repeat),
        "results": [asdict(r) for r in results],
    }

    os.makedirs("results", exist_ok=True)
    out_file = f"results/benchmark-{run_id}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(suite, f, indent=2, ensure_ascii=False)

    yield {"type": "done", "run_id": run_id, "out_file": out_file, "suite": suite}
