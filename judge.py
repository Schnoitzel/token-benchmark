#!/usr/bin/env python3
"""
judge.py - blinde Qualitaetsbewertung (LLM-as-judge).

Vergleicht fuer JEDE Kombination (gleiche Aufgabe, gleiches Modell) die Antwort
von Pi gegen die von Claude Code. Ein unabhaengiges, staerkeres Modell (Opus)
bewertet beide BLIND ("A" vs "B"), positions-bereinigt (Swap-Test).

Anti-Bias-Massnahmen:
  - Blind: der Richter erfaehrt nicht, welche Antwort von welchem Harness ist.
  - Swap-Test: jede Paarung wird zweimal bewertet, mit vertauschtem A/B.
    Stimmt das Urteil nicht ueberein -> Positions-Bias -> zaehlt als "tie".
  - Unabhaengiger Richter: NIE ein Modell sich selbst bewerten lassen.
    Standard-Richter = Opus 4.8. Werden Opus-Antworten bewertet, wird auf das
    naechstbeste Modell (Sonnet 4.6) ausgewichen.

Der Richter laeuft ueber Pi (leichtester Harness, blank, in Sandbox) - seine
Tokens zaehlen NICHT zum Benchmark, das ist eine Meta-Auswertung.

Aufruf:
  python3 judge.py                              # neueste Ergebnisdatei
  python3 judge.py results/benchmark-xxxx.json  # bestimmte Datei

Ergebnis wird in dieselbe JSON unter dem Schluessel "quality" geschrieben.
"""

import glob
import json
import statistics
import sys

from models import MODELS
from runners import run_pi
from tasks import Task

# Richter-Konfiguration
DEFAULT_JUDGE = "Opus 4.8"
FALLBACK_JUDGE = "Sonnet 4.6"   # falls Opus sich selbst bewerten muesste

CRITERIA = ["korrektheit", "vollstaendigkeit", "anweisungstreue", "klarheit", "praegnanz"]


def model_by_label(label: str):
    return next((m for m in MODELS if m.label == label), None)


def pick_judge(contestant_label: str):
    """Waehlt den Richter. Nie das gleiche Modell wie die Kandidaten."""
    judge_label = DEFAULT_JUDGE if contestant_label != DEFAULT_JUDGE else FALLBACK_JUDGE
    return judge_label, model_by_label(judge_label)


# --- Judge-Prompt -----------------------------------------------------------

def build_prompt(task_prompt: str, ans_a: str, ans_b: str) -> str:
    return (
        "Du bist ein strenger, unparteiischer Bewerter von KI-Antworten. "
        "Zwei Antworten (A und B) wurden auf dieselbe Aufgabe gegeben. "
        "Bewerte sie ausschliesslich nach Inhalt, nicht nach Stil-Vorlieben.\n\n"
        "AUFGABE (identisch an beide gestellt):\n"
        "---\n" + task_prompt + "\n---\n\n"
        "ANTWORT A:\n---\n" + (ans_a or "(leer)") + "\n---\n\n"
        "ANTWORT B:\n---\n" + (ans_b or "(leer)") + "\n---\n\n"
        "Bewerte JEDE Antwort einzeln nach diesen Kriterien (Ganzzahl 1-5, 5=beste):\n"
        "- korrektheit: Stimmen Fakten/Code/Logik?\n"
        "- vollstaendigkeit: Sind alle geforderten Teile enthalten?\n"
        "- anweisungstreue: Wurden Vorgaben (z.B. Laenge, Format) eingehalten?\n"
        "- klarheit: Verstaendlich und gut strukturiert?\n"
        "- praegnanz: Kein Fuellmaterial, kein Geschwafel?\n\n"
        "Bestimme den Gewinner: \"A\", \"B\" oder \"tie\" (wenn gleichwertig).\n\n"
        "Antworte AUSSCHLIESSLICH mit einem JSON-Objekt in GENAU diesem Format, "
        "ohne weitere Worte, ohne Markdown:\n"
        '{"scores_A":{"korrektheit":0,"vollstaendigkeit":0,"anweisungstreue":0,'
        '"klarheit":0,"praegnanz":0},'
        '"scores_B":{"korrektheit":0,"vollstaendigkeit":0,"anweisungstreue":0,'
        '"klarheit":0,"praegnanz":0},'
        '"winner":"A","confidence":"hoch","justification":"<ein knapper Satz auf Deutsch>"}'
    )


def extract_json(text: str) -> dict | None:
    """Holt das erste vollstaendige JSON-Objekt aus einem Text (robust gegen
    Code-Fences/Begleittext)."""
    if not text:
        return None
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
        start = text.find("{", start + 1)
    return None


def run_judge_once(judge_model, task_prompt: str, ans_a: str, ans_b: str) -> dict | None:
    """Eine Bewertung. Gibt geparstes JSON oder None bei Fehler."""
    prompt = build_prompt(task_prompt, ans_a, ans_b)
    t = Task(id="judge", complexity="baseline", description="judge", prompt=prompt, use_tools=False)
    res = run_pi(t, judge_model)
    if res.error:
        return None
    return extract_json(res.response)


def overall(scores: dict) -> float:
    vals = [scores.get(c, 0) for c in CRITERIA]
    return statistics.mean(vals) if vals else 0.0


# --- Eine Paarung bewerten (mit Swap-Test) ----------------------------------

def judge_pair(pi_ans: str, cc_ans: str, task_prompt: str, judge_model) -> dict:
    """Bewertet Pi vs Claude Code positions-bereinigt.

    Durchlauf 1: A=Pi,  B=Claude  -> winner A bedeutet Pi
    Durchlauf 2: A=Claude, B=Pi   -> winner A bedeutet Claude
    """
    p1 = run_judge_once(judge_model, task_prompt, pi_ans, cc_ans)
    p2 = run_judge_once(judge_model, task_prompt, cc_ans, pi_ans)

    if not p1 or not p2:
        return {"error": "Richter-Antwort nicht auswertbar", "raw1": p1, "raw2": p2}

    # Gewinner aus beiden Durchlaeufen auf pi/cc abbilden
    def map_winner(p, a_is_pi: bool) -> str:
        w = p.get("winner", "tie")
        if w == "tie":
            return "tie"
        if w == "A":
            return "pi" if a_is_pi else "cc"
        if w == "B":
            return "cc" if a_is_pi else "pi"
        return "tie"

    w1 = map_winner(p1, a_is_pi=True)
    w2 = map_winner(p2, a_is_pi=False)

    position_bias = (w1 != w2)
    consensus = w1 if not position_bias else "tie"

    # Scores auf pi/cc abbilden und ueber beide Durchlaeufe mitteln
    pi_scores_runs = [p1.get("scores_A", {}), p2.get("scores_B", {})]
    cc_scores_runs = [p1.get("scores_B", {}), p2.get("scores_A", {})]

    def avg_scores(runs: list[dict]) -> dict:
        return {c: statistics.mean([r.get(c, 0) for r in runs]) for c in CRITERIA}

    pi_scores = avg_scores(pi_scores_runs)
    cc_scores = avg_scores(cc_scores_runs)

    return {
        "winner": consensus,
        "position_bias": position_bias,
        "pi_scores": pi_scores,
        "cc_scores": cc_scores,
        "pi_overall": overall(pi_scores),
        "cc_overall": overall(cc_scores),
        "justification": p1.get("justification", ""),
        "raw": {"pass1": p1, "pass2": p2},
    }


# --- Hauptlauf --------------------------------------------------------------

def representative(results: list[dict], task_id: str, model_label: str, harness: str) -> dict | None:
    """Erste fehlerfreie Wiederholung einer Kombination."""
    cands = [
        r for r in results
        if r["task_id"] == task_id and r["model_label"] == model_label
        and r["harness"] == harness and not r.get("error")
    ]
    cands.sort(key=lambda r: r.get("repeat_index", 0))
    return cands[0] if cands else None


def judge_suite_iter(suite: dict):
    """Generator: liefert Fortschritts-Ereignisse und am Ende das Quality-Dict.

      {"type": "judge_start", "total"}
      {"type": "judge_progress", "index", "total", "task_id", "model_label", "judge", "verdict": {...}}
      {"type": "judge_done", "quality": {...}}
    """
    results = suite["results"]
    pairs_keys = []
    seen = set()
    for r in results:
        key = (r["task_id"], r["model_label"])
        if key not in seen:
            seen.add(key)
            pairs_keys.append(key)

    # Nur paarweise vergleichbare Kombinationen
    pairs = []
    for task_id, model_label in pairs_keys:
        pi_r = representative(results, task_id, model_label, "pi")
        cc_r = representative(results, task_id, model_label, "claude-code")
        if pi_r and cc_r:
            pairs.append((task_id, model_label, pi_r, cc_r))

    total = len(pairs)
    yield {"type": "judge_start", "total": total}

    judgements = []
    for idx, (task_id, model_label, pi_r, cc_r) in enumerate(pairs, start=1):
        judge_label, judge_model = pick_judge(model_label)
        if judge_model is None:
            continue
        verdict = judge_pair(pi_r["response"], cc_r["response"], pi_r["task_prompt"], judge_model)
        verdict.update({
            "task_id": task_id,
            "model_label": model_label,
            "task_complexity": pi_r["task_complexity"],
            "judge": judge_label,
        })
        judgements.append(verdict)
        yield {
            "type": "judge_progress",
            "index": idx,
            "total": total,
            "task_id": task_id,
            "model_label": model_label,
            "judge": judge_label,
            "verdict": verdict,
        }

    quality = {
        "judge_default": DEFAULT_JUDGE,
        "judge_fallback": FALLBACK_JUDGE,
        "criteria": CRITERIA,
        "method": "blind, A/B randomisiert, Swap-Test (2 Durchlaeufe je Paar)",
        "judgements": judgements,
        "summary": summarize(judgements),
    }
    yield {"type": "judge_done", "quality": quality}


def judge_suite(suite: dict) -> dict:
    """Blockierende Variante (fuer CLI): druckt Fortschritt, gibt Quality zurueck."""
    quality = {}
    for ev in judge_suite_iter(suite):
        if ev["type"] == "judge_progress":
            v = ev["verdict"]
            print(f"  [{ev['index']}/{ev['total']}] {ev['task_id']} / {ev['model_label']}  (Richter: {ev['judge']})")
            if "error" in v:
                print(f"    ⚠ {v['error']}")
            else:
                print(f"    Sieger: {v['winner']}  (Pi {v['pi_overall']:.2f} vs CC {v['cc_overall']:.2f}"
                      f"{', Positions-Bias' if v['position_bias'] else ''})")
        elif ev["type"] == "judge_done":
            quality = ev["quality"]
    return quality


def summarize(judgements: list[dict]) -> dict:
    valid = [j for j in judgements if "error" not in j]
    wins = {"pi": 0, "cc": 0, "tie": 0}
    bias = 0
    pi_overall, cc_overall = [], []
    for j in valid:
        wins[j["winner"]] = wins.get(j["winner"], 0) + 1
        if j.get("position_bias"):
            bias += 1
        pi_overall.append(j["pi_overall"])
        cc_overall.append(j["cc_overall"])
    pi_mean = statistics.mean(pi_overall) if pi_overall else 0.0
    cc_mean = statistics.mean(cc_overall) if cc_overall else 0.0
    return {
        "n_pairs": len(valid),
        "n_errors": len(judgements) - len(valid),
        "wins": wins,
        "position_bias_count": bias,
        "pi_mean_score": pi_mean,
        "cc_mean_score": cc_mean,
        "score_delta": cc_mean - pi_mean,  # >0: CC besser, <0: Pi besser
    }


def print_summary(quality: dict) -> None:
    s = quality["summary"]
    print("\n" + "=" * 70)
    print(f"QUALITAETSVERGLEICH  (Richter: {quality['judge_default']}, {quality['method']})")
    print("-" * 70)
    print(f"  {'':<22}{'Pi':>12}{'Claude Code':>16}")
    print(f"  {'Ø Gesamtscore (1-5)':<22}{s['pi_mean_score']:>12.2f}{s['cc_mean_score']:>16.2f}")
    print(f"  {'Siege':<22}{s['wins']['pi']:>12}{s['wins']['cc']:>16}")
    print(f"  {'Unentschieden':<22}{s['wins']['tie']:>12}")
    print(f"  {'Positions-Bias erkannt':<22}{s['position_bias_count']:>12}")
    print(f"  {'Paare bewertet':<22}{s['n_pairs']:>12}")
    if s["n_errors"]:
        print(f"  {'(Fehler/uebersprungen)':<22}{s['n_errors']:>12}")
    print("-" * 70)
    delta = s["score_delta"]
    if abs(delta) < 0.25:
        print(f"  → Kein bedeutsamer Qualitaetsunterschied (Δ {delta:+.2f} Punkte).")
    elif delta > 0:
        print(f"  → Claude Code im Schnitt {delta:+.2f} Punkte besser.")
    else:
        print(f"  → Pi im Schnitt {-delta:+.2f} Punkte besser.")
    print()


def load_suite(path: str | None) -> tuple[str, dict]:
    if path is None:
        files = sorted(glob.glob("results/benchmark-*.json"))
        if not files:
            raise SystemExit("Keine Ergebnisdateien in results/ gefunden.")
        path = files[-1]
        print(f"Lade {path}")
    with open(path, encoding="utf-8") as f:
        return path, json.load(f)


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else None
    path, suite = load_suite(path)

    print("\nStarte blinde Qualitaetsbewertung (je Paar 2 Durchlaeufe, Swap-Test)...\n")
    quality = judge_suite(suite)
    suite["quality"] = quality

    with open(path, "w", encoding="utf-8") as f:
        json.dump(suite, f, indent=2, ensure_ascii=False)

    print_summary(quality)
    print(f"Bewertung gespeichert in {path}")
    print("Tipp: 'python3 report.py' erzeugt den Bericht inkl. Qualitaetsabschnitt.\n")


if __name__ == "__main__":
    main()
