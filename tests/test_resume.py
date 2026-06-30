"""Tests fuer die Resume-Funktion (core.py).

Prueft:
- run_plan wird korrekt im Suite-JSON gespeichert
- Resume ueberspringt genau die bereits erledigten Runs
- Resume mit leerem Done-Set = normaler Lauf
- Resume mit vollstaendigem Done-Set = kein Run mehr
- is_complete / total korrekt in /api/results
"""

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import core
from models import Model
from runners import RunResult, TokenUsage
from tasks import Task

MODEL_A = Model(label="Haiku 4.5", pi_model="claude-haiku-4-5", cc_model="haiku", tier="cheap")
MODEL_B = Model(label="Sonnet 4.6", pi_model="claude-sonnet-4-6", cc_model="sonnet", tier="mid")
TASK = Task(id="baseline-overhead", complexity="baseline", description="d",
            prompt="Reply with exactly: OK", use_tools=False)


FAKE_USAGE = {
    "input_tokens": 100, "output_tokens": 5, "cache_read": 0,
    "cache_write": 0, "total_tokens": 105, "cost_usd": 0.0,
    "cost_harness_usd": None,
}


def _fake_result(harness="pi", model_label="Haiku 4.5", task_id="baseline-overhead"):
    return RunResult(
        harness=harness, model_label=model_label, task_id=task_id,
        task_complexity="baseline", task_prompt="p", duration_ms=50,
        usage=TokenUsage(input_tokens=100, output_tokens=5, cache_read=0,
                         cache_write=0, total_tokens=105, cost_usd=0.0),
        response="OK", timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _run_in_tmp(harnesses, models, tasks, repeat=1, resume_run_id=None):
    """Fuehrt run_benchmark_iter in einem temp-Verzeichnis aus; gibt Events zurueck."""
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            with patch.object(core, "run_pi",
                              side_effect=lambda t, m: _fake_result("pi", m.label, t.id)), \
                 patch.object(core, "run_claude",
                              side_effect=lambda t, m: _fake_result("claude-code", m.label, t.id)), \
                 patch.object(core, "get_tool_versions",
                              return_value={"pi": "test", "claude": "test"}):
                events = list(core.run_benchmark_iter(
                    harnesses=harnesses, models=models, tasks=tasks,
                    delay=0, repeat=repeat, resume_run_id=resume_run_id,
                ))
        finally:
            os.chdir(cwd)
    return events


# ---------------------------------------------------------------------------
# run_plan im Suite-JSON
# ---------------------------------------------------------------------------

class TestRunPlan(unittest.TestCase):
    def test_run_plan_in_suite_gespeichert(self):
        events = _run_in_tmp(["pi"], [MODEL_A], [TASK], repeat=2)
        suite = events[-1]["suite"]
        self.assertIn("run_plan", suite)
        plan = suite["run_plan"]
        self.assertEqual(plan["task_ids"], ["baseline-overhead"])
        self.assertEqual(plan["model_labels"], ["Haiku 4.5"])
        self.assertEqual(plan["harnesses"], ["pi"])
        self.assertEqual(plan["repeat"], 2)
        self.assertEqual(plan["total"], 2)  # 1 task x 1 modell x 1 harness x 2

    def test_run_plan_total_stimmt_bei_mehreren_kombinationen(self):
        events = _run_in_tmp(["pi", "claude-code"], [MODEL_A, MODEL_B], [TASK], repeat=3)
        plan = events[-1]["suite"]["run_plan"]
        # 2 harnesses x 2 modelle x 1 task x 3 repeat = 12
        self.assertEqual(plan["total"], 12)


# ---------------------------------------------------------------------------
# Resume: ueberspringt bereits erledigte Runs
# ---------------------------------------------------------------------------

class TestResume(unittest.TestCase):
    def _make_partial_suite(self, tmp_dir, run_id, done_results):
        """Schreibt eine unvollstaendige Suite-JSON in tmp_dir/results/."""
        os.makedirs(os.path.join(tmp_dir, "results"), exist_ok=True)
        suite = {
            "run_id": run_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "run_plan": {
                "task_ids": ["baseline-overhead"],
                "model_labels": ["Haiku 4.5"],
                "harnesses": ["pi", "claude-code"],
                "repeat": 3,
                "total": 6,
            },
            "provenance": {"repeat": 3},
            "results": done_results,
            "aggregates": [],
        }
        fp = os.path.join(tmp_dir, "results", f"benchmark-{run_id}.json")
        with open(fp, "w") as f:
            json.dump(suite, f)
        return fp

    def _done_entry(self, harness, repeat_index, model_label="Haiku 4.5",
                    task_id="baseline-overhead"):
        """Hilfsmethode: fertiger Result-Dict mit realistischen usage-Feldern."""
        return {
            "harness": harness, "model_label": model_label,
            "task_id": task_id, "repeat_index": repeat_index,
            "task_complexity": "baseline", "task_prompt": "p",
            "duration_ms": 50, "usage": FAKE_USAGE,
            "response": "OK",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": None,
        }

    def test_resume_ueberspringt_erledigte_runs(self):
        """Wenn 2 von 6 Runs schon erledigt sind, werden genau 4 neue ausgefuehrt."""
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                run_id = "test1234"
                done = [
                    self._done_entry("pi", 0),
                    self._done_entry("pi", 1),
                ]
                self._make_partial_suite(tmp, run_id, done)

                calls_pi = []
                calls_cc = []

                def fake_pi(t, m):
                    calls_pi.append((t.id, m.label))
                    return _fake_result("pi", m.label, t.id)

                def fake_cc(t, m):
                    calls_cc.append((t.id, m.label))
                    return _fake_result("claude-code", m.label, t.id)

                with patch.object(core, "run_pi", side_effect=fake_pi), \
                     patch.object(core, "run_claude", side_effect=fake_cc), \
                     patch.object(core, "get_tool_versions",
                                  return_value={"pi": "t", "claude": "t"}):
                    events = list(core.run_benchmark_iter(
                        harnesses=["pi", "claude-code"],
                        models=[MODEL_A],
                        tasks=[TASK],
                        delay=0, repeat=3,
                        resume_run_id=run_id,
                    ))
            finally:
                os.chdir(cwd)

        result_events = [e for e in events if e["type"] == "result"]
        # 2 schon erledigt, 4 noch offen → 4 neue Results
        self.assertEqual(len(result_events), 4)
        # run_pi wurde nur 1 Mal aufgerufen (repeat_index 2 fehlt noch)
        self.assertEqual(len(calls_pi), 1)
        # run_claude wurde 3 Mal aufgerufen (alle 3 repeats)
        self.assertEqual(len(calls_cc), 3)

    def test_resume_behaelt_run_id(self):
        """Resume schreibt in dieselbe Datei (gleiche run_id)."""
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                run_id = "abcd5678"
                self._make_partial_suite(tmp, run_id, [])

                with patch.object(core, "run_pi",
                                  side_effect=lambda t, m: _fake_result("pi", m.label, t.id)), \
                     patch.object(core, "run_claude",
                                  side_effect=lambda t, m: _fake_result("claude-code", m.label, t.id)), \
                     patch.object(core, "get_tool_versions",
                                  return_value={"pi": "t", "claude": "t"}):
                    events = list(core.run_benchmark_iter(
                        harnesses=["pi", "claude-code"],
                        models=[MODEL_A], tasks=[TASK],
                        delay=0, repeat=3,
                        resume_run_id=run_id,
                    ))
            finally:
                os.chdir(cwd)

        done_event = events[-1]
        self.assertEqual(done_event["run_id"], run_id)

    def test_resume_mit_leerem_done_set_laeuft_komplett(self):
        """Resume ohne erledigte Runs = normaler Vollauf."""
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                run_id = "zero0000"
                self._make_partial_suite(tmp, run_id, [])

                with patch.object(core, "run_pi",
                                  side_effect=lambda t, m: _fake_result("pi", m.label, t.id)), \
                     patch.object(core, "run_claude",
                                  side_effect=lambda t, m: _fake_result("claude-code", m.label, t.id)), \
                     patch.object(core, "get_tool_versions",
                                  return_value={"pi": "t", "claude": "t"}):
                    events = list(core.run_benchmark_iter(
                        harnesses=["pi", "claude-code"],
                        models=[MODEL_A], tasks=[TASK],
                        delay=0, repeat=3,
                        resume_run_id=run_id,
                    ))
            finally:
                os.chdir(cwd)

        result_events = [e for e in events if e["type"] == "result"]
        self.assertEqual(len(result_events), 6)  # alle 6

    def test_resume_mit_vollem_done_set_produziert_keine_runs(self):
        """Resume wenn alles fertig → 0 neue Runs, done-Event trotzdem."""
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                run_id = "full1234"
                # Alle 6 Runs als erledigt markieren
                done = [
                    self._done_entry(h, rep)
                    for h in ["pi", "claude-code"]
                    for rep in range(3)
                ]
                self._make_partial_suite(tmp, run_id, done)

                with patch.object(core, "run_pi",
                                  side_effect=lambda t, m: _fake_result("pi", m.label, t.id)), \
                     patch.object(core, "run_claude",
                                  side_effect=lambda t, m: _fake_result("claude-code", m.label, t.id)), \
                     patch.object(core, "get_tool_versions",
                                  return_value={"pi": "t", "claude": "t"}):
                    events = list(core.run_benchmark_iter(
                        harnesses=["pi", "claude-code"],
                        models=[MODEL_A], tasks=[TASK],
                        delay=0, repeat=3,
                        resume_run_id=run_id,
                    ))
            finally:
                os.chdir(cwd)

        result_events = [e for e in events if e["type"] == "result"]
        self.assertEqual(len(result_events), 0)
        # done-Event muss trotzdem kommen
        self.assertEqual(events[-1]["type"], "done")

    def test_suite_enthaelt_alle_results_nach_resume(self):
        """Nach Resume: Suite-JSON hat bestehende + neue Results zusammen."""
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                run_id = "merge123"
                done = [self._done_entry("pi", 0)]
                self._make_partial_suite(tmp, run_id, done)

                with patch.object(core, "run_pi",
                                  side_effect=lambda t, m: _fake_result("pi", m.label, t.id)), \
                     patch.object(core, "run_claude",
                                  side_effect=lambda t, m: _fake_result("claude-code", m.label, t.id)), \
                     patch.object(core, "get_tool_versions",
                                  return_value={"pi": "t", "claude": "t"}):
                    events = list(core.run_benchmark_iter(
                        harnesses=["pi", "claude-code"],
                        models=[MODEL_A], tasks=[TASK],
                        delay=0, repeat=3,
                        resume_run_id=run_id,
                    ))
            finally:
                os.chdir(cwd)

        suite = events[-1]["suite"]
        # 1 vorher + 5 neue = 6 gesamt
        self.assertEqual(len(suite["results"]), 6)


# ---------------------------------------------------------------------------
# is_complete in /api/results
# ---------------------------------------------------------------------------

class TestIsComplete(unittest.TestCase):
    """Prueft dass /api/results korrekte is_complete/total-Felder liefert."""

    def setUp(self):
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import server
        self.server = server

    def _write_suite(self, tmp, run_id, num_results, total, finished_at=None):
        os.makedirs(os.path.join(tmp, "results"), exist_ok=True)
        results = []
        for i in range(num_results):
            results.append({
                "harness": "pi", "model_label": "Haiku 4.5",
                "task_id": "baseline-overhead", "repeat_index": i,
            })
        suite = {
            "run_id": run_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": finished_at,
            "run_plan": {"total": total},
            "results": results,
        }
        fp = os.path.join(tmp, "results", f"benchmark-{run_id}.json")
        with open(fp, "w") as f:
            json.dump(suite, f)

    def test_vollstaendiger_lauf_ist_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write_suite(tmp, "done1234", num_results=6, total=6,
                              finished_at=datetime.now(timezone.utc).isoformat())
            items = self.server.build_results_list(os.path.join(tmp, "results"))
        item = next(i for i in items if i["run_id"] == "done1234")
        self.assertTrue(item["is_complete"])
        self.assertEqual(item["total"], 6)

    def test_unvollstaendiger_lauf_ist_nicht_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write_suite(tmp, "part5678", num_results=39, total=540,
                              finished_at=None)
            items = self.server.build_results_list(os.path.join(tmp, "results"))
        item = next(i for i in items if i["run_id"] == "part5678")
        self.assertFalse(item["is_complete"])
        self.assertEqual(item["total"], 540)


if __name__ == "__main__":
    unittest.main()


class TestAtomicSave(unittest.TestCase):
    """Prueft atomisches Schreiben: alte Datei bleibt bei Absturz erhalten."""

    def _run_one(self, tmp_dir):
        """Hilfsfunktion: fuehrt einen minimalen Benchmark-Lauf durch."""
        cwd = os.getcwd()
        os.chdir(tmp_dir)
        try:
            with patch.object(core, "run_pi",
                              side_effect=lambda t, m: _fake_result("pi", m.label, t.id)), \
                 patch.object(core, "run_claude",
                              side_effect=lambda t, m: _fake_result("claude-code", m.label, t.id)), \
                 patch.object(core, "get_tool_versions",
                              return_value={"pi": "test", "claude": "test"}):
                list(core.run_benchmark_iter(
                    tasks=[TASK], models=[MODEL_A], harnesses=["pi", "claude-code"],
                    delay=0, repeat=1,
                ))
        finally:
            os.chdir(cwd)
        # Gibt den Pfad zur erzeugten JSON zurueck (liegt in results/)
        results_dir = os.path.join(tmp_dir, "results")
        files = [f for f in os.listdir(results_dir) if f.endswith(".json")]
        return os.path.join(results_dir, files[0]) if files else None

    def test_tmp_datei_wird_nach_save_geloescht(self):
        """Nach erfolgreichem Speichern darf keine .tmp-Datei uebrig bleiben."""
        with tempfile.TemporaryDirectory() as tmp:
            out_file = self._run_one(tmp)
            self.assertTrue(os.path.exists(out_file), "JSON muss existieren")
            self.assertFalse(
                os.path.exists(out_file + ".tmp"),
                ".tmp darf nach erfolgreichem Schreiben nicht mehr existieren",
            )

    def test_alte_datei_bleibt_bei_schreibfehler_erhalten(self):
        """Wenn der Schreibvorgang abbricht, bleibt die alte JSON unveraendert."""
        import json as _json
        with tempfile.TemporaryDirectory() as tmp:
            # Ersten Lauf abschliessen -> gueltige JSON vorhanden
            out_file = self._run_one(tmp)
            with open(out_file) as f:
                original = f.read()
            original_count = len(_json.loads(original)["results"])

            # Zweiten Schreibvorgang simulieren der mitten im dump abbricht
            original_dump = _json.dump
            call_count = [0]

            def crashing_dump(obj, fp, **kw):
                call_count[0] += 1
                # Beim zweiten Aufruf (= naechster _save) absichtlich abbrechen
                if call_count[0] >= 2:
                    fp.write('{"broken":')  # absichtlich kaputtes JSON
                    raise OSError("Simulierter Schreibfehler")
                return original_dump(obj, fp, **kw)

            with patch("json.dump", side_effect=crashing_dump):
                try:
                    self._run_one(tmp)
                except OSError:
                    pass  # erwarteter Fehler

            # Alte Datei muss noch lesbar und unveraendert sein
            with open(out_file) as f:
                recovered = f.read()
            recovered_data = _json.loads(recovered)  # darf nicht kaputt sein
            self.assertEqual(
                len(recovered_data["results"]), original_count,
                "Alte JSON muss nach Schreibfehler unveraendert sein",
            )
