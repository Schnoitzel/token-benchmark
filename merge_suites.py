#!/usr/bin/env python3
"""Fuehrt zwei Benchmark-Suiten zu einer zusammen, indem die Ergebnisse EINES
Tasks aus der Basis-Suite durch die eines spaeteren (faireren) Laufs ersetzt
werden.

Hintergrund: Der grosse Referenzlauf (540 Runs) wurde mit Claude Code als
Windows-Binary gefahren. Dadurch sind die Tool-/Mehrschritt-Ergebnisse
(`medium-bash`) durch eine Plattform-Asymmetrie verfaelscht (siehe
docs/adr/0004-plattform-asymmetrie-cc-windows-pi-linux.md). Die Single-Turn-
Tasks bleiben gueltig (OS-unabhaengig). Dieses Skript ersetzt nur den betroffenen
Task durch einen sauberen Linux-Container-Lauf und berechnet die Aggregate neu.

Die Provenienz wird EHRLICH gekennzeichnet: das Ergebnis ist eine gemischte
Suite (Single-Turn aus dem Windows-Lauf, medium-bash aus dem Container-Lauf).

Aufruf:
  python3 merge_suites.py <basis.json> <override.json> <task_id> [out.json]
"""
import json
import sys
import uuid
from datetime import datetime, timezone

import stats


def merge(base_path: str, override_path: str, task_id: str, out_path: str | None) -> str:
    with open(base_path, encoding="utf-8") as f:
        base = json.load(f)
    with open(override_path, encoding="utf-8") as f:
        override = json.load(f)

    # 1) Basis ohne den zu ersetzenden Task
    kept = [r for r in base["results"] if r.get("task_id") != task_id]
    # 2) Ersatz-Runs aus der Override-Suite (nur der betroffene Task)
    replacement = [r for r in override["results"] if r.get("task_id") == task_id]

    if not replacement:
        raise SystemExit(f"Override-Suite enthaelt keine Runs fuer Task '{task_id}'.")

    n_removed = len(base["results"]) - len(kept)
    combined = kept + replacement
    print(f"Basis-Runs gesamt:        {len(base['results'])}")
    print(f"  davon '{task_id}' entfernt: {n_removed}")
    print(f"  Single-Turn behalten:    {len(kept)}")
    print(f"Ersatz-Runs ('{task_id}'):  {len(replacement)}")
    print(f"Kombiniert gesamt:         {len(combined)}")

    # 3) Aggregate komplett neu berechnen (Median/Streuung je Kombination)
    aggregates = stats.build_aggregates(combined)

    # 4) Provenienz ehrlich kennzeichnen
    run_id = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc).isoformat()
    base_prov = dict(base.get("provenance", {}))
    over_prov = override.get("provenance", {})
    base_prov["merge_provenance"] = {
        "merged_at": now,
        "base_suite": base.get("run_id"),
        "base_tool_versions": base.get("provenance", {}).get("tool_versions"),
        "base_platform": base.get("provenance", {}).get("platform"),
        "overridden_task": task_id,
        "override_suite": override.get("run_id"),
        "override_tool_versions": over_prov.get("tool_versions"),
        "override_platform": over_prov.get("platform"),
        "reason": (
            f"'{task_id}' wurde im Basis-Lauf durch Plattform-Asymmetrie "
            "(Claude Code als Windows-Binary, Pi unter Linux) verfaelscht "
            "(ADR-0004). Ersetzt durch fairen Lauf, in dem beide Harnesses "
            "nativ unter Linux liefen."
        ),
        "warning": (
            "GEMISCHTE PROVENIENZ: Single-Turn-Tasks stammen aus dem Basis-Lauf "
            "(Claude Code Windows-Binary), '" + task_id + "' aus dem Container-"
            "Lauf (Claude Code Linux). Der Overhead pro Anfrage ist fuer Single-"
            "Turn-Tasks OS-unabhaengig und damit vergleichbar; der Claude-Code-"
            "Versionsunterschied ist hier dokumentiert."
        ),
    }

    out = {
        "run_id": run_id,
        # started_at = Merge-Zeitpunkt, damit die kombinierte Suite in der
        # UI-Liste klar von der originalen Basis-Suite unterscheidbar ist.
        "started_at": now,
        "finished_at": now,
        "run_plan": base.get("run_plan"),
        "provenance": base_prov,
        "results": combined,
        "aggregates": aggregates,
    }
    # Qualitaet uebernehmen, falls in der Basis vorhanden
    if "quality" in base:
        out["quality"] = base["quality"]

    if out_path is None:
        out_path = f"results/benchmark-{run_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nGespeichert: {out_path}  (run_id={run_id})")
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    base_p, over_p, task = sys.argv[1], sys.argv[2], sys.argv[3]
    out_p = sys.argv[4] if len(sys.argv) > 4 else None
    merge(base_p, over_p, task, out_p)
