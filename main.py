#!/usr/bin/env python3
"""
main.py - Einstiegspunkt fuer den Benchmark (Kommandozeile).

Nutzt dieselbe Logik wie die Web-UI (core.run_benchmark_iter), damit CLI und
UI identische Ergebnisse, einheitliche Kosten und denselben Provenienz-Block
erzeugen.

Aufruf:
  python3 main.py [optionen]

Optionen:
  --harnesses pi,claude-code         Welche Harnesses (Standard: beide)
  --models    "Haiku 4.5,Sonnet 4.6" Kommagetrennte Modell-Labels
  --tasks     trivial-fact,simple-code Kommagetrennte Task-IDs
  --complexity trivial,simple        Tasks nach Komplexitaet filtern
  --repeat    5                      Wiederholungen pro Kombination (Standard: 1)
  --delay     2.0                    Pause zwischen Runs in Sekunden (Standard: 2)
  --dry-run                          Nur anzeigen, was laufen wuerde
  --no-report                        Keinen Report nach dem Run erzeugen

Beispiele:
  python3 main.py --dry-run
  python3 main.py --complexity baseline --repeat 5
  python3 main.py --complexity trivial --models "Sonnet 4.6"
"""

import argparse
import subprocess
import sys

from core import filter_models, filter_tasks, run_benchmark_iter
from utils import fmt_cost

# --- ANSI-Farben ------------------------------------------------------------
RESET = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
GREEN = "\033[32m"; YELLOW = "\033[33m"; RED = "\033[31m"
CYAN = "\033[36m"; MAGENTA = "\033[35m"


def print_result(r: dict) -> None:
    color = CYAN if r["harness"] == "pi" else MAGENTA
    status = f"{RED}x FEHLER{RESET}" if r.get("error") else f"{GREEN}ok{RESET}"
    u = r["usage"]
    print(
        f"  {status} {color}{BOLD}{r['harness']}{RESET} {DIM}[{r['model_label']}]{RESET} "
        f"total={BOLD}{u['total_tokens']:,}{RESET} "
        f"(in={u['input_tokens']} out={u['output_tokens']} "
        f"cache_r={u['cache_read']} cache_w={u['cache_write']}) "
        f"kosten={YELLOW}{fmt_cost(u['cost_usd'])}{RESET} "
        f"{DIM}{r['duration_ms']/1000:.1f}s{RESET}"
    )
    if r.get("error"):
        print(f"    {RED}{r['error'][:200]}{RESET}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Token-Benchmark Pi vs Claude Code")
    p.add_argument("--harnesses", default="pi,claude-code")
    p.add_argument("--models", default=None)
    p.add_argument("--tasks", default=None)
    p.add_argument("--complexity", default=None)
    p.add_argument("--repeat", type=int, default=1)
    p.add_argument("--delay", type=float, default=2.0)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-report", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    harnesses = [h.strip() for h in args.harnesses.split(",") if h.strip()]
    only_models = [m.strip() for m in args.models.split(",")] if args.models else None
    only_tasks = [t.strip() for t in args.tasks.split(",")] if args.tasks else None
    complexity = [c.strip() for c in args.complexity.split(",")] if args.complexity else None

    tasks = filter_tasks(only_tasks, complexity)
    models = filter_models(only_models)
    repeat = max(1, args.repeat)
    total = len(tasks) * len(models) * len(harnesses) * repeat

    # --- Dry-run -----------------------------------------------------------
    if args.dry_run:
        print("\nTROCKENLAUF - wuerde ausfuehren:\n")
        for t in tasks:
            for m in models:
                for h in harnesses:
                    print(f"  {h:<14}{m.label:<14}{t.id}  x{repeat}")
        print(f"\nGesamt: {total} Runs (repeat={repeat})\n")
        return

    print(f"\n{BOLD}+{'='*51}+{RESET}")
    print(f"{BOLD}|  Token-Benchmark{' '*35}|{RESET}")
    print(f"{BOLD}+{'='*51}+{RESET}\n")
    print(f"  Tasks      : {len(tasks)}  ({', '.join(t.id for t in tasks)})")
    print(f"  Modelle    : {', '.join(m.label for m in models)}")
    print(f"  Harnesses  : {', '.join(harnesses)}")
    print(f"  Wiederhol. : {repeat}")
    print(f"  Gesamt     : {total} Runs\n")

    out_file = None
    cur_task = None

    for event in run_benchmark_iter(harnesses, models, tasks, delay=args.delay, repeat=repeat):
        if event["type"] == "run_start":
            if event["task"] != cur_task:
                cur_task = event["task"]
                print(f"\n{BOLD}> Task: {cur_task}{RESET}")
            rep = f" (Lauf {event['repeat']}/{event['repeats']})" if event["repeats"] > 1 else ""
            print(f"  [{event['index']}/{event['total']}] {event['harness']} / {event['model']}{rep} ...")
        elif event["type"] == "result":
            print_result(event["result"])
        elif event["type"] == "done":
            out_file = event["out_file"]

    print(f"\n{GREEN}{BOLD}Fertig.{RESET} Ergebnisse gespeichert in {out_file}\n")

    # --- Report ------------------------------------------------------------
    if not args.no_report and out_file:
        try:
            subprocess.run([sys.executable, "report.py", out_file], check=True)
        except subprocess.CalledProcessError:
            print("(Report-Erzeugung fehlgeschlagen - manuell: python3 report.py)")


if __name__ == "__main__":
    main()
