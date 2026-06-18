"""Tests fuer den blinden LLM-Richter (judge.py).

Kein echter Modell-Aufruf: run_judge_once wird gemockt, damit die
Mapping-/Swap-Logik deterministisch geprueft werden kann.
"""

import unittest
from unittest.mock import patch

import judge


class TestExtractJson(unittest.TestCase):
    def test_sauberes_json(self):
        self.assertEqual(judge.extract_json('{"winner":"A"}'), {"winner": "A"})

    def test_json_in_code_fence(self):
        text = 'Hier mein Urteil:\n```json\n{"winner":"B"}\n```\nFertig.'
        self.assertEqual(judge.extract_json(text), {"winner": "B"})

    def test_json_mit_begleittext(self):
        text = 'Antwort: {"winner":"tie","confidence":"hoch"} -- das wars'
        self.assertEqual(
            judge.extract_json(text), {"winner": "tie", "confidence": "hoch"}
        )

    def test_verschachtelte_objekte(self):
        text = '{"scores_A":{"korrektheit":5},"winner":"A"}'
        self.assertEqual(
            judge.extract_json(text),
            {"scores_A": {"korrektheit": 5}, "winner": "A"},
        )

    def test_kaputtes_json_gibt_none(self):
        self.assertIsNone(judge.extract_json('{"winner": }'))

    def test_kein_json_gibt_none(self):
        self.assertIsNone(judge.extract_json("nur text, keine klammern"))

    def test_leerer_string_gibt_none(self):
        self.assertIsNone(judge.extract_json(""))

    def test_nimmt_erstes_vollstaendiges_objekt(self):
        text = '{"winner":"A"} dann noch {"winner":"B"}'
        self.assertEqual(judge.extract_json(text), {"winner": "A"})

    def test_geschweifte_klammern_im_string(self):
        # ein '{' im String-Wert darf das Parsen nicht zerstoeren
        text = '{"j": "ein {falscher} text", "winner": "A"}'
        self.assertEqual(
            judge.extract_json(text), {"j": "ein {falscher} text", "winner": "A"}
        )


class TestOverall(unittest.TestCase):
    def test_mittelwert_aller_kriterien(self):
        scores = {c: 4 for c in judge.CRITERIA}
        self.assertEqual(judge.overall(scores), 4.0)

    def test_fehlende_kriterien_zaehlen_als_null(self):
        # nur 'korrektheit'=5, restliche 4 fehlen (=0) -> (5+0+0+0+0)/5 = 1.0
        self.assertEqual(judge.overall({"korrektheit": 5}), 1.0)


class TestPickJudge(unittest.TestCase):
    def test_normaler_kandidat_bekommt_opus_richter(self):
        label, model = judge.pick_judge("Sonnet 4.6")
        self.assertEqual(label, judge.DEFAULT_JUDGE)
        self.assertIsNotNone(model)

    def test_opus_kandidat_bekommt_fallback_richter(self):
        # Opus darf nicht sich selbst bewerten
        label, model = judge.pick_judge("Opus 4.8")
        self.assertEqual(label, judge.FALLBACK_JUDGE)
        self.assertNotEqual(label, judge.DEFAULT_JUDGE)


def _verdict(winner, score_a, score_b):
    """Baut eine Richter-Antwort mit gleichmaessigen Scores fuer A und B."""
    return {
        "winner": winner,
        "scores_A": {c: score_a for c in judge.CRITERIA},
        "scores_B": {c: score_b for c in judge.CRITERIA},
        "justification": "Testbegruendung",
    }


class TestJudgePairSwap(unittest.TestCase):
    def test_pi_gewinnt_konsistent_ohne_bias(self):
        # Durchlauf1: A=pi,B=cc -> winner A (=pi)
        # Durchlauf2: A=cc,B=pi -> winner B (=pi)
        with patch.object(judge, "run_judge_once",
                          side_effect=[_verdict("A", 5, 2), _verdict("B", 2, 5)]):
            res = judge.judge_pair("pi-antwort", "cc-antwort", "prompt", judge_model=None)
        self.assertEqual(res["winner"], "pi")
        self.assertFalse(res["position_bias"])
        self.assertGreater(res["pi_overall"], res["cc_overall"])

    def test_cc_gewinnt_konsistent(self):
        # Durchlauf1: A=pi,B=cc -> winner B (=cc)
        # Durchlauf2: A=cc,B=pi -> winner A (=cc)
        with patch.object(judge, "run_judge_once",
                          side_effect=[_verdict("B", 2, 5), _verdict("A", 5, 2)]):
            res = judge.judge_pair("pi", "cc", "prompt", judge_model=None)
        self.assertEqual(res["winner"], "cc")
        self.assertFalse(res["position_bias"])

    def test_positions_bias_fuehrt_zu_tie(self):
        # beide Durchlaeufe waehlen "A" -> einmal pi, einmal cc -> Widerspruch
        with patch.object(judge, "run_judge_once",
                          side_effect=[_verdict("A", 5, 2), _verdict("A", 5, 2)]):
            res = judge.judge_pair("pi", "cc", "prompt", judge_model=None)
        self.assertTrue(res["position_bias"])
        self.assertEqual(res["winner"], "tie")

    def test_scores_werden_ueber_swap_gemittelt(self):
        # pi bekommt in P1 (scores_A)=4 und in P2 (scores_B)=2 -> Mittel 3
        with patch.object(judge, "run_judge_once",
                          side_effect=[_verdict("tie", 4, 1), _verdict("tie", 1, 2)]):
            res = judge.judge_pair("pi", "cc", "prompt", judge_model=None)
        # pi_scores = avg(P1.scores_A=4, P2.scores_B=2) = 3
        self.assertAlmostEqual(res["pi_overall"], 3.0, places=6)
        # cc_scores = avg(P1.scores_B=1, P2.scores_A=1) = 1
        self.assertAlmostEqual(res["cc_overall"], 1.0, places=6)

    def test_konsistenter_sieger_mit_verschiedenen_scores(self):
        # beide Durchlaeufe waehlen den Pi-Slot, aber mit unterschiedlichen Scores
        # P1: A=pi -> winner A; P2: B=pi -> winner B  => konsistent pi, kein Bias
        with patch.object(judge, "run_judge_once",
                          side_effect=[_verdict("A", 5, 1), _verdict("B", 3, 1)]):
            res = judge.judge_pair("pi", "cc", "prompt", judge_model=None)
        self.assertEqual(res["winner"], "pi")
        self.assertFalse(res["position_bias"])
        # pi = avg(P1.scores_A=5, P2.scores_B=1) = 3
        self.assertAlmostEqual(res["pi_overall"], 3.0, places=6)

    def test_erster_durchlauf_none_gibt_fehler(self):
        with patch.object(judge, "run_judge_once", side_effect=[None, _verdict("A", 5, 2)]):
            res = judge.judge_pair("pi", "cc", "prompt", judge_model=None)
        self.assertIn("error", res)

    def test_zweiter_durchlauf_none_gibt_fehler(self):
        with patch.object(judge, "run_judge_once", side_effect=[_verdict("A", 5, 2), None]):
            res = judge.judge_pair("pi", "cc", "prompt", judge_model=None)
        self.assertIn("error", res)

    def test_beide_durchlaeufe_none_gibt_fehler(self):
        with patch.object(judge, "run_judge_once", side_effect=[None, None]):
            res = judge.judge_pair("pi", "cc", "prompt", judge_model=None)
        self.assertIn("error", res)


class TestSummarize(unittest.TestCase):
    def test_zaehlt_siege_und_bias(self):
        judgements = [
            {"winner": "pi", "position_bias": False, "pi_overall": 4.0, "cc_overall": 3.0},
            {"winner": "cc", "position_bias": True, "pi_overall": 2.0, "cc_overall": 4.0},
            {"error": "kaputt"},
        ]
        s = judge.summarize(judgements)
        self.assertEqual(s["n_pairs"], 2)
        self.assertEqual(s["n_errors"], 1)
        self.assertEqual(s["wins"]["pi"], 1)
        self.assertEqual(s["wins"]["cc"], 1)
        self.assertEqual(s["position_bias_count"], 1)
        # score_delta = cc_mean - pi_mean = 3.5 - 3.0 = 0.5
        self.assertAlmostEqual(s["score_delta"], 0.5, places=6)

    def test_leere_liste_crasht_nicht(self):
        s = judge.summarize([])
        self.assertEqual(s["n_pairs"], 0)
        self.assertEqual(s["wins"], {"pi": 0, "cc": 0, "tie": 0})
        self.assertEqual(s["score_delta"], 0.0)


if __name__ == "__main__":
    unittest.main()
