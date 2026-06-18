"""
Report-Generator.

Liest eine Benchmark-JSON und erzeugt:
  - eine Konsolen-Zusammenfassung
  - einen Markdown-Bericht (results/report-<runId>.md)

Wasserdicht-Features:
  - aggregiert ueber Wiederholungen (Median + Spanne min-max + n)
  - einheitliche Kosten (kommen bereits aus pricing.py im JSON)
  - eigener Baseline-Block (reiner Harness-Overhead)
  - Provenienz-Block (Versionen, Flags, Preise, Plattform)

Aufruf:
  python3 report.py                              # neueste Ergebnisdatei
  python3 report.py results/benchmark-xxxx.json  # bestimmte Datei
"""

import glob
import json
import os
import statistics
import sys
from collections import defaultdict

# Reihenfolge der Komplexitaetsstufen (Baseline zuerst)
ORDER = ["baseline", "trivial", "simple", "medium", "complex"]


def order_idx(complexity: str) -> int:
    return ORDER.index(complexity) if complexity in ORDER else len(ORDER)


def load_suite(path: str | None) -> dict:
    if path is None:
        files = sorted(glob.glob("results/benchmark-*.json"))
        if not files:
            raise SystemExit("Keine Ergebnisdateien in results/ gefunden.")
        path = files[-1]
        print(f"Lade {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --- Aggregation ------------------------------------------------------------

def med(nums: list[float]) -> float:
    return statistics.median(nums) if nums else 0.0


def dig(row: dict, keys: tuple[str, ...]):
    v = row
    for k in keys:
        v = v[k]
    return v


def median_of(rows: list[dict], *keys) -> float:
    """Median eines (verschachtelten) Feldes ueber alle (Wiederholungs-)Zeilen."""
    return med([dig(r, keys) for r in rows]) if rows else 0.0


def spread(rows: list[dict], *keys) -> tuple[float, float, float, int]:
    """(median, min, max, n) eines Feldes."""
    vals = [dig(r, keys) for r in rows]
    if not vals:
        return 0.0, 0.0, 0.0, 0
    return med(vals), min(vals), max(vals), len(vals)


def fmt_cost(usd: float) -> str:
    if usd < 0.001:
        return f"{usd * 1000:.3f}m$"
    return f"${usd:.5f}"


def fmt_n(n: float) -> str:
    return f"{round(n):,}"


def ratio(a: float, b: float) -> str:
    if not a or not b:
        return "n/a"
    r = a / b
    return f"{r:.1f}x" if r >= 1 else f"{1 / r:.1f}x weniger"


# --- Konsolen-Zusammenfassung ----------------------------------------------

def print_summary(suite: dict) -> None:
    results = [r for r in suite["results"] if not r.get("error")]
    repeat = suite.get("provenance", {}).get("repeat", 1)

    print("\n" + "=" * 100)
    print(f"BENCHMARK-ZUSAMMENFASSUNG  -  Run {suite['run_id']}  (Wiederholungen: {repeat}, Median-Werte)")
    print("=" * 100)

    by_task_model: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in results:
        by_task_model[(r["task_id"], r["model_label"])].append(r)

    for (task_id, model_label), group in sorted(
        by_task_model.items(),
        key=lambda kv: (order_idx(kv[1][0]["task_complexity"]), kv[0][0], kv[0][1]),
    ):
        pi = [r for r in group if r["harness"] == "pi"]
        cc = [r for r in group if r["harness"] == "claude-code"]
        complexity = group[0]["task_complexity"]

        pi_total = median_of(pi, "usage", "total_tokens")
        cc_total = median_of(cc, "usage", "total_tokens")
        pi_cache = median_of(pi, "usage", "cache_read") + median_of(pi, "usage", "cache_write")
        cc_cache = median_of(cc, "usage", "cache_read") + median_of(cc, "usage", "cache_write")

        n_pi = len(pi)
        n_cc = len(cc)
        print(f"\n  Task: {task_id}  |  Modell: {model_label}  |  Komplexitaet: {complexity}  |  n=(pi:{n_pi}, cc:{n_cc})")
        print("  " + "-" * 78)
        print(f"  {'Metrik (Median)':<30}{'Pi':>14}{'Claude Code':>16}{'Faktor':>14}")
        print("  " + "-" * 74)

        rows = [
            ("Total Tokens", pi_total, cc_total, False),
            ("  - Cache (System-Prompt)", pi_cache, cc_cache, False),
            ("  - Input (User-Nachricht)", median_of(pi, "usage", "input_tokens"), median_of(cc, "usage", "input_tokens"), False),
            ("  - Output (Antwort)", median_of(pi, "usage", "output_tokens"), median_of(cc, "usage", "output_tokens"), False),
            ("Kosten (USD)", median_of(pi, "usage", "cost_usd"), median_of(cc, "usage", "cost_usd"), True),
            ("Dauer (ms)", median_of(pi, "duration_ms"), median_of(cc, "duration_ms"), False),
        ]
        for label, pv, cv, is_cost in rows:
            ps = fmt_cost(pv) if is_cost else f"{round(pv):,}"
            cs = fmt_cost(cv) if is_cost else f"{round(cv):,}"
            print(f"  {label:<30}{ps:>14}{cs:>16}{ratio(cv, pv):>14}")

    # System-Prompt-Overhead pro Modell (Median)
    print("\n" + "=" * 100)
    print("SYSTEM-PROMPT-OVERHEAD (Cache+Input bei Baseline = System-Prompt + Tool-Definitionen)")
    print("-" * 100)
    print(f"  {'Modell':<18}{'Pi Overhead':>20}{'CC Overhead':>20}{'CC/Pi':>14}")
    print("  " + "-" * 72)
    for model_label, pi_ov, cc_ov in _overhead_rows(results):
        print(f"  {model_label:<18}{round(pi_ov):>20,}{round(cc_ov):>20,}{ratio(cc_ov, pi_ov):>14}")
    print()

    # Qualitaet (falls vorhanden)
    quality = suite.get("quality")
    if quality:
        s = quality["summary"]
        print("=" * 100)
        print(f"QUALITAETSVERGLEICH (Richter: {quality.get('judge_default')}, {quality.get('method')})")
        print("-" * 100)
        print(f"  {'':<24}{'Pi':>12}{'Claude Code':>16}")
        print(f"  {'O Gesamtscore (1-5)':<24}{s['pi_mean_score']:>12.2f}{s['cc_mean_score']:>16.2f}")
        print(f"  {'Siege':<24}{s['wins']['pi']:>12}{s['wins']['cc']:>16}")
        print(f"  {'Unentschieden':<24}{s['wins']['tie']:>12}")
        print(f"  {'Positions-Bias':<24}{s['position_bias_count']:>12}")
        delta = s['score_delta']
        verdict = ("kein bedeutsamer Unterschied" if abs(delta) < 0.25
                   else ("CC besser" if delta > 0 else "Pi besser"))
        print("-" * 100)
        print(f"  => Delta {delta:+.2f} Punkte ({verdict})")
        print()


def _overhead_rows(results: list[dict]):
    """Liefert (modell, pi_overhead_median, cc_overhead_median).

    Bevorzugt die Baseline-Aufgabe (reiner Overhead). Gibt es keine, faellt es
    auf den Cache-Median ueber alle Aufgaben zurueck.
    """
    baseline = [r for r in results if r["task_complexity"] == "baseline"]
    use = baseline if baseline else results

    def ov(r):
        u = r["usage"]
        return u["input_tokens"] + u["cache_read"] + u["cache_write"]

    by_model: dict[str, list[dict]] = defaultdict(list)
    for r in use:
        by_model[r["model_label"]].append(r)

    out = []
    for model_label, group in by_model.items():
        pi = [ov(r) for r in group if r["harness"] == "pi"]
        cc = [ov(r) for r in group if r["harness"] == "claude-code"]
        out.append((model_label, med(pi), med(cc)))
    return out


# --- Markdown-Bericht -------------------------------------------------------

def build_markdown(suite: dict) -> str:
    all_results = suite["results"]
    results = [r for r in all_results if not r.get("error")]
    prov = suite.get("provenance", {})
    repeat = prov.get("repeat", 1)
    L: list[str] = []

    L.append("# Token-Verbrauch Benchmark - Pi vs Claude Code")
    L.append("")
    L.append(f"**Run-ID:** `{suite['run_id']}`  ")
    L.append(f"**Start:** {suite['started_at']}  ")
    L.append(f"**Ende:** {suite['finished_at']}  ")
    L.append(f"**Wiederholungen je Kombination:** {repeat} (alle Zahlen sind Mediane)  ")
    L.append("")
    L.append("## Kurzfassung")
    L.append("")
    L.append(
        "Dieser Benchmark misst den Token-Overhead zweier KI-Coding-Harnesses - "
        "**Pi** (minimalistisch) und **Claude Code** (funktionsreich) - bei "
        "identischen Prompts, identischen Modellen und in identisch sauberer "
        "Umgebung (leeres Arbeitsverzeichnis, kein Projektkontext)."
    )
    L.append("")

    # --- Baseline-Overhead (Kernzahl) --------------------------------------
    baseline = [r for r in results if r["task_complexity"] == "baseline"]
    if baseline:
        L.append("## Baseline: reiner Harness-Overhead")
        L.append("")
        L.append(
            "Gemessen mit einem Trivial-Prompt. Die Antwort ist winzig, daher ist "
            "`Input + Cache` praktisch nur **System-Prompt + Tool-Definitionen**, "
            "die jeder Harness bei **jeder** Anfrage mitschickt - unabhaengig von "
            "Aufgabe und Antwortlaenge. Das ist die belastbarste Overhead-Kennzahl."
        )
        L.append("")
        L.append("| Modell | Pi Overhead-Tokens | Claude Code Overhead-Tokens | Faktor |")
        L.append("|--------|-------------------:|----------------------------:|-------:|")
        for model_label, pi_ov, cc_ov in _overhead_rows(baseline):
            L.append(f"| {model_label} | {round(pi_ov):,} | {round(cc_ov):,} | **{ratio(cc_ov, pi_ov)}** |")
        L.append("")

    # --- System-Prompt-Overhead pro Modell ---------------------------------
    L.append("## System-Prompt-Overhead je Modell")
    L.append("")
    L.append("Median der `Input + Cache`-Tokens (= mitgeschickter Kontext ohne Antwort).")
    L.append("")
    L.append("| Modell | Pi | Claude Code | Faktor |")
    L.append("|--------|---:|------------:|-------:|")
    for model_label, pi_ov, cc_ov in _overhead_rows(results):
        L.append(f"| {model_label} | {round(pi_ov):,} | {round(cc_ov):,} | **{ratio(cc_ov, pi_ov)}** |")
    L.append("")

    # --- Qualitaet (LLM-as-judge) ------------------------------------------
    quality = suite.get("quality")
    if quality:
        s = quality["summary"]
        delta = s["score_delta"]
        if abs(delta) < 0.25:
            verdict = f"**Kein bedeutsamer Qualitaetsunterschied** (Δ {delta:+.2f} Punkte)"
        elif delta > 0:
            verdict = f"Claude Code im Schnitt **{delta:+.2f}** Punkte besser"
        else:
            verdict = f"Pi im Schnitt **{-delta:+.2f}** Punkte besser"
        L.append("## Qualitaetsvergleich (blinder LLM-Richter)")
        L.append("")
        L.append(
            f"Richter: **{quality.get('judge_default')}** "
            f"(Ausweich-Richter fuer Opus-Antworten: {quality.get('judge_fallback')}). "
            f"Methode: {quality.get('method')}."
        )
        L.append("")
        L.append("| Kennzahl | Pi | Claude Code |")
        L.append("|----------|---:|------------:|")
        L.append(f"| Ø Gesamtscore (1-5) | {s['pi_mean_score']:.2f} | {s['cc_mean_score']:.2f} |")
        L.append(f"| Siege | {s['wins']['pi']} | {s['wins']['cc']} |")
        L.append(f"| Unentschieden | {s['wins']['tie']} | |")
        L.append(f"| Positions-Bias erkannt | {s['position_bias_count']} | |")
        L.append(f"| Paare bewertet | {s['n_pairs']} | |")
        L.append("")
        L.append(f"**Fazit:** {verdict}.")
        L.append("")
        # Einzelne Urteile
        L.append("| Aufgabe | Modell | Sieger | Pi-Score | CC-Score | Begruendung |")
        L.append("|---------|--------|--------|---------:|---------:|-------------|")
        order_j = sorted(
            [j for j in quality["judgements"] if "error" not in j],
            key=lambda j: (order_idx(j.get("task_complexity", "")), j["task_id"], j["model_label"]),
        )
        for j in order_j:
            just = (j.get("justification", "") or "").replace("|", "/")
            L.append(
                f"| {j['task_id']} | {j['model_label']} | {j['winner']} | "
                f"{j['pi_overall']:.2f} | {j['cc_overall']:.2f} | {just} |"
            )
        L.append("")

    # --- Ergebnisse pro Task & Modell (aggregiert) -------------------------
    L.append("## Ergebnisse pro Task & Modell")
    L.append("")
    L.append(f"Aggregiert ueber {repeat} Wiederholung(en): **Median**, in Klammern **min-max** bei Total & Kosten.")
    L.append("")

    tasks_seen: dict[str, dict] = {}
    for r in results:
        tasks_seen.setdefault(r["task_id"], r)
    sorted_tasks = sorted(tasks_seen.values(), key=lambda r: (order_idx(r["task_complexity"]), r["task_id"]))

    for tr in sorted_tasks:
        task_id = tr["task_id"]
        L.append(f"### {task_id}")
        L.append("")
        L.append(f"- **Komplexitaet:** {tr['task_complexity']}")
        L.append("")
        L.append("| Modell | Harness | n | Input | Output | Cache R | Cache W | Total (min-max) | Kosten (min-max) | Dauer |")
        L.append("|--------|---------|--:|------:|-------:|--------:|--------:|----------------:|-----------------:|------:|")

        task_results = [r for r in results if r["task_id"] == task_id]
        # nach (modell, harness) aggregieren
        by_mh: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for r in task_results:
            by_mh[(r["model_label"], r["harness"])].append(r)

        for (model_label, harness), rows in sorted(by_mh.items()):
            t_med, t_min, t_max, n = spread(rows, "usage", "total_tokens")
            c_med, c_min, c_max, _ = spread(rows, "usage", "cost_usd")
            d_med = median_of(rows, "duration_ms")
            L.append(
                f"| {model_label} | {harness} | {n} | "
                f"{fmt_n(median_of(rows, 'usage', 'input_tokens'))} | "
                f"{fmt_n(median_of(rows, 'usage', 'output_tokens'))} | "
                f"{fmt_n(median_of(rows, 'usage', 'cache_read'))} | "
                f"{fmt_n(median_of(rows, 'usage', 'cache_write'))} | "
                f"{fmt_n(t_med)} ({fmt_n(t_min)}-{fmt_n(t_max)}) | "
                f"{fmt_cost(c_med)} ({fmt_cost(c_min)}-{fmt_cost(c_max)}) | "
                f"{round(d_med/100)/10}s |"
            )
        L.append("")

    # --- Antworten (je Kombination eine repraesentative) -------------------
    L.append("## Antworten")
    L.append("")
    L.append("_Je Kombination eine repraesentative Antwort (erste Wiederholung) zur qualitativen Bewertung._")
    L.append("")

    for tr in sorted_tasks:
        task_id = tr["task_id"]
        L.append(f"### {task_id} - Antworten")
        L.append("")
        L.append("**Prompt:**")
        L.append("")
        L.append("```")
        L.append(tr["task_prompt"])
        L.append("```")
        L.append("")

        task_results = [r for r in all_results if r["task_id"] == task_id]
        by_m: dict[str, list[dict]] = defaultdict(list)
        for r in task_results:
            by_m[r["model_label"]].append(r)

        for model_label, group in by_m.items():
            L.append(f"#### {model_label}")
            L.append("")
            # je Harness die erste Wiederholung
            seen_harness = set()
            for r in sorted(group, key=lambda r: (r["harness"], r.get("repeat_index", 0))):
                if r["harness"] in seen_harness:
                    continue
                seen_harness.add(r["harness"])
                u = r["usage"]
                L.append(f"**{r['harness']}** ({fmt_n(u['total_tokens'])} Tokens, {fmt_cost(u['cost_usd'])}):")
                L.append("")
                if r.get("error"):
                    L.append(f"> (!) Fehler: {r['error']}")
                else:
                    L.append(r["response"] or "_leere Antwort_")
                L.append("")

    # --- Methodik & Provenienz ---------------------------------------------
    L.append("## Methodik & Provenienz")
    L.append("")
    if prov:
        tv = prov.get("tool_versions", {})
        L.append(f"- **Pi-Version:** `{tv.get('pi', '?')}`")
        L.append(f"- **Claude-Code-Version:** `{tv.get('claude', '?')}`")
        L.append(f"- **Pi-Flags:** `{prov.get('flags', {}).get('pi', '')}`")
        L.append(f"- **Claude-Code-Flags:** `{prov.get('flags', {}).get('claude', '')}`")
        L.append(f"- **Umgebung:** {prov.get('sandbox', '')}")
        L.append(f"- **Wiederholungen:** {prov.get('repeat', 1)}")
        L.append(f"- **Kostenbasis:** {prov.get('cost_basis', '')}")
        prices = prov.get("pricing_usd_per_mtok", {})
        if prices:
            price_str = ", ".join(
                f"{m}: in ${v['input']}/MTok · out ${v['output']}/MTok" for m, v in prices.items()
            )
            L.append(f"- **Preise:** {price_str}")
        cm = prov.get("cache_multipliers", {})
        if cm:
            L.append(f"- **Cache-Faktoren:** write ×{cm.get('write')} · read ×{cm.get('read')} (relativ zum Input-Preis)")
        L.append(f"- **Plattform:** {prov.get('platform', '')} · Python {prov.get('python', '')}")
    L.append("- Token-Zahlen stammen direkt aus den API-Antworten der Harnesses.")
    L.append("- `cache_write` = System-Prompt beim ersten Auftreten, `cache_read` bei Folgeaufrufen.")
    L.append("- Kosten werden fuer **beide** Harnesses einheitlich aus den Token-Zahlen berechnet (pricing.py).")

    # Fehlerhinweis
    n_err = sum(1 for r in all_results if r.get("error"))
    if n_err:
        L.append("")
        L.append(f"> ⚠ {n_err} Lauf/Laeufe mit Fehler wurden aus den Statistiken ausgeschlossen.")

    return "\n".join(L)


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else None
    suite = load_suite(path)

    print_summary(suite)

    md = build_markdown(suite)
    out_path = f"results/report-{suite['run_id']}.md"
    os.makedirs("results", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Markdown-Bericht geschrieben nach {out_path}\n")


if __name__ == "__main__":
    main()
