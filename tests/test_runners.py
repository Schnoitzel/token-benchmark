"""Tests fuer das Token-Parsing der Runner (runners.py).

Kein echter Subprozess: runners._run_process wird gemockt und mit den ECHTEN
Fixtures (tests/fixtures/) gefuettert. So pruefen wir das Parsing gegen reale
Pi-/Claude-Ausgaben, inkl. Timeout- und Fehlerpfaden.
"""

import os
import unittest
from unittest.mock import patch

import runners
from models import Model
from tasks import Task

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _fix(name: str) -> str:
    """Fixture lazy lesen (nicht beim Import) – fehlende Datei bricht dann nur
    den einzelnen Test, nicht das gesamte Modul."""
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return f.read()

TASK = Task(id="t", complexity="baseline", description="d", prompt="Reply with exactly: OK", use_tools=False)
MODEL = Model(label="Haiku 4.5", pi_model="claude-haiku-4-5", cc_model="haiku", tier="cheap")


class TestRunPi(unittest.TestCase):
    def test_parst_echte_ausgabe(self):
        with patch.object(runners, "_run_process", return_value=(_fix("pi_turn_end.jsonl"), "", False)):
            res = runners.run_pi(TASK, MODEL)
        self.assertEqual(res.harness, "pi")
        self.assertIsNone(res.error)
        self.assertEqual(res.response, "OK")
        u = res.usage
        self.assertEqual(u.input_tokens, 3068)
        self.assertEqual(u.output_tokens, 4)
        self.assertEqual(u.cache_read, 0)
        self.assertEqual(u.cache_write, 0)
        self.assertEqual(u.total_tokens, 3072)
        self.assertAlmostEqual(u.cost_usd, 0.003088, places=6)

    def test_timeout_setzt_fehler(self):
        with patch.object(runners, "_run_process", return_value=("", "", True)):
            res = runners.run_pi(TASK, MODEL)
        self.assertIsNotNone(res.error)
        self.assertIn("Timeout", res.error)

    def test_ohne_turn_end_setzt_fehler(self):
        muell = '{"type":"session"}\n{"type":"agent_start"}\n'
        with patch.object(runners, "_run_process", return_value=(muell, "", False)):
            res = runners.run_pi(TASK, MODEL)
        self.assertIsNotNone(res.error)
        self.assertIn("turn_end", res.error)

    def test_ignoriert_kaputte_jsonl_zeilen(self):
        # eine kaputte Zeile zwischen gueltigen Events darf nicht crashen
        out = "kaputt{nicht json\n" + _fix("pi_turn_end.jsonl")
        with patch.object(runners, "_run_process", return_value=(out, "", False)):
            res = runners.run_pi(TASK, MODEL)
        self.assertIsNone(res.error)
        self.assertEqual(res.response, "OK")


class TestRunClaude(unittest.TestCase):
    def test_parst_echte_ausgabe(self):
        with patch.object(runners, "_run_process", return_value=(_fix("claude_result.json"), "", False)):
            res = runners.run_claude(TASK, MODEL)
        self.assertEqual(res.harness, "claude-code")
        self.assertIsNone(res.error)
        self.assertEqual(res.response, "OK")
        u = res.usage
        self.assertEqual(u.input_tokens, 10)
        self.assertEqual(u.output_tokens, 57)
        self.assertEqual(u.cache_read, 21506)
        self.assertEqual(u.cache_write, 7714)
        self.assertEqual(u.total_tokens, 10 + 57 + 21506 + 7714)
        self.assertAlmostEqual(u.cost_usd, 0.0125891, places=7)

    def test_timeout_setzt_fehler(self):
        with patch.object(runners, "_run_process", return_value=("", "", True)):
            res = runners.run_claude(TASK, MODEL)
        self.assertIsNotNone(res.error)
        self.assertIn("Timeout", res.error)

    def test_kaputtes_json_setzt_fehler(self):
        with patch.object(runners, "_run_process", return_value=("kein json", "", False)):
            res = runners.run_claude(TASK, MODEL)
        self.assertIsNotNone(res.error)
        self.assertIn("JSON-Parsing", res.error)

    def test_is_error_flag_setzt_fehler(self):
        bad = '{"usage":{"input_tokens":1,"output_tokens":1,"cache_read_input_tokens":0,' \
              '"cache_creation_input_tokens":0},"total_cost_usd":0.0,"result":"oops",' \
              '"is_error":true,"subtype":"error_max_turns"}'
        with patch.object(runners, "_run_process", return_value=(bad, "", False)):
            res = runners.run_claude(TASK, MODEL)
        self.assertIsNotNone(res.error)


class TestOverheadBefund(unittest.TestCase):
    """Dokumentiert den Kern-Befund direkt an den echten Fixtures:
    CC-Overhead (input+cache) ist um ein Vielfaches groesser als Pi."""

    def test_cc_overhead_deutlich_groesser_als_pi(self):
        with patch.object(runners, "_run_process", return_value=(_fix("pi_turn_end.jsonl"), "", False)):
            pi = runners.run_pi(TASK, MODEL)
        with patch.object(runners, "_run_process", return_value=(_fix("claude_result.json"), "", False)):
            cc = runners.run_claude(TASK, MODEL)

        def overhead(u):
            return u.input_tokens + u.cache_read + u.cache_write

        pi_ov = overhead(pi.usage)
        cc_ov = overhead(cc.usage)
        # Fixtures sind EINGEFRORENE Echtdaten (Pi 3068 vs CC 29230 = ~9.5x).
        # Schwelle bewusst hoch (>6x), damit der Test die Groessenordnung wirklich absichert.
        self.assertGreater(cc_ov, pi_ov * 6)


if __name__ == "__main__":
    unittest.main()
