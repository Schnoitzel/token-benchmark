"""Tests fuer die Orchestrierungs-Logik (core.py).

run_pi/run_claude werden gemockt -> keine echten Aufrufe. Der Generator
run_benchmark_iter wird in einem temporaeren Arbeitsverzeichnis ausgefuehrt,
damit die geschriebene results/-Datei den echten Ordner nicht verschmutzt.
"""

import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import core
from models import Model
from runners import RunResult, TokenUsage
from tasks import Task

MODEL = Model(label="Haiku 4.5", pi_model="claude-haiku-4-5", cc_model="haiku", tier="cheap")
TASK = Task(id="baseline-overhead", complexity="baseline", description="d",
            prompt="Reply with exactly: OK", use_tools=False)


def fake_result(harness):
    return RunResult(
        harness=harness, model_label="Haiku 4.5", task_id="baseline-overhead",
        task_complexity="baseline", task_prompt="p", duration_ms=100,
        usage=TokenUsage(input_tokens=1000, output_tokens=10, cache_read=0,
                         cache_write=0, total_tokens=1010, cost_usd=0.0),
        response="OK", timestamp=datetime.now(timezone.utc).isoformat(),
    )


class TestFilter(unittest.TestCase):
    def test_filter_models_none_gibt_alle(self):
        self.assertEqual(len(core.filter_models(None)), len(core.MODELS))

    def test_filter_models_nach_label(self):
        out = core.filter_models(["Sonnet 4.6"])
        self.assertEqual([m.label for m in out], ["Sonnet 4.6"])

    def test_filter_models_nach_pi_id(self):
        out = core.filter_models(["claude-haiku-4-5"])
        self.assertEqual([m.label for m in out], ["Haiku 4.5"])

    def test_filter_tasks_nach_komplexitaet(self):
        out = core.filter_tasks(None, ["baseline"])
        self.assertTrue(all(t.complexity == "baseline" for t in out))
        self.assertTrue(len(out) >= 1)

    def test_filter_tasks_nach_id(self):
        out = core.filter_tasks(["trivial-math"], None)
        self.assertEqual([t.id for t in out], ["trivial-math"])


class TestApplyUnifiedCost(unittest.TestCase):
    def test_ueberschreibt_kosten_und_bewahrt_harness_wert(self):
        res = fake_result("pi")
        res.usage.cost_usd = 0.42          # angeblich vom Harness gemeldet
        res.usage.input_tokens = 1_000_000  # 1 MTok input
        res.usage.output_tokens = 0
        core.apply_unified_cost(res)
        # Harness-Eigenangabe bleibt erhalten
        self.assertEqual(res.usage.cost_harness_usd, 0.42)
        # einheitliche Kosten = 1 MTok * 1.00 USD (Haiku input) = 1.00
        self.assertAlmostEqual(res.usage.cost_usd, 1.00, places=6)


class TestRunBenchmarkIter(unittest.TestCase):
    def _run(self, **kwargs):
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                with patch.object(core, "run_pi", side_effect=lambda t, m: fake_result("pi")), \
                     patch.object(core, "run_claude", side_effect=lambda t, m: fake_result("claude-code")), \
                     patch.object(core, "get_tool_versions", return_value={"pi": "test", "claude": "test"}):
                    events = list(core.run_benchmark_iter(
                        harnesses=["pi", "claude-code"], models=[MODEL], tasks=[TASK],
                        delay=0, **kwargs))
            finally:
                os.chdir(cwd)
        return events

    def test_event_sequenz(self):
        events = self._run(repeat=1)
        self.assertEqual(events[0]["type"], "start")
        self.assertEqual(events[-1]["type"], "done")
        types = [e["type"] for e in events]
        # 1 task x 1 modell x 2 harnesses x repeat 1 = 2 Laeufe
        self.assertEqual(types.count("run_start"), 2)
        self.assertEqual(types.count("result"), 2)

    def test_repeat_vervielfacht_laeufe(self):
        events = self._run(repeat=3)
        # 2 harnesses x repeat 3 = 6 Laeufe
        self.assertEqual(events[0]["total"], 6)
        self.assertEqual(sum(1 for e in events if e["type"] == "result"), 6)
        # repeat_index laeuft 0..2 pro Harness
        idxs = sorted(e["result"]["repeat_index"] for e in events if e["type"] == "result")
        self.assertEqual(idxs, [0, 0, 1, 1, 2, 2])

    def test_done_enthaelt_suite_mit_provenance(self):
        events = self._run(repeat=1)
        done = events[-1]
        self.assertIn("suite", done)
        self.assertIn("provenance", done["suite"])
        self.assertEqual(done["suite"]["provenance"]["repeat"], 1)
        self.assertEqual(len(done["suite"]["results"]), 2)


if __name__ == "__main__":
    unittest.main()
