"""Tests fuer die Streuungs-/Statistik-Helfer (stats.py)."""

import unittest

import stats


class TestEinzelmasse(unittest.TestCase):
    def test_median(self):
        self.assertEqual(stats.median([3, 1, 2]), 2)
        self.assertEqual(stats.median([1, 2, 3, 4]), 2.5)

    def test_minmax(self):
        self.assertEqual(stats.minmax([5, 1, 3]), (1, 5))

    def test_stdev_stichprobe(self):
        # [10,12,14] -> Stichproben-Stdev = sqrt((4+0+4)/2) = 2.0
        self.assertAlmostEqual(stats.stdev([10, 12, 14]), 2.0, places=6)

    def test_stdev_bei_n1_ist_null(self):
        self.assertEqual(stats.stdev([42]), 0.0)

    def test_iqr(self):
        # inklusive Methode: Q1=2, Q3=4 -> IQR=2
        self.assertAlmostEqual(stats.iqr([1, 2, 3, 4, 5]), 2.0, places=6)

    def test_rel_spread(self):
        # (max-min)/median = (14-10)/12
        self.assertAlmostEqual(stats.rel_spread([10, 12, 14]), 4 / 12, places=6)

    def test_rel_spread_bei_n1_ist_null(self):
        self.assertEqual(stats.rel_spread([7]), 0.0)


class TestSummary(unittest.TestCase):
    def test_summary_felder(self):
        s = stats.summary([10, 12, 14])
        self.assertEqual(s["n"], 3)
        self.assertEqual(s["median"], 12)
        self.assertEqual(s["min"], 10)
        self.assertEqual(s["max"], 14)
        self.assertAlmostEqual(s["mean"], 12.0, places=6)
        self.assertAlmostEqual(s["stdev"], 2.0, places=6)
        self.assertAlmostEqual(s["rel_spread"], 4 / 12, places=6)

    def test_summary_leer(self):
        s = stats.summary([])
        self.assertEqual(s["n"], 0)
        self.assertEqual(s["median"], 0.0)
        self.assertEqual(s["stdev"], 0.0)
        self.assertEqual(s["rel_spread"], 0.0)

    def test_summary_einzelwert(self):
        s = stats.summary([5])
        self.assertEqual(s["n"], 1)
        self.assertEqual(s["median"], 5)
        self.assertEqual(s["min"], 5)
        self.assertEqual(s["max"], 5)
        self.assertEqual(s["stdev"], 0.0)


def _res(harness, task="baseline-overhead", model="Haiku 4.5", complexity="baseline",
         inp=0, out=0, cr=0, cw=0, total=None, cost=0.0, dur=1000, error=None):
    if total is None:
        total = inp + out + cr + cw
    return {
        "harness": harness, "task_id": task, "model_label": model,
        "task_complexity": complexity, "duration_ms": dur, "error": error,
        "usage": {"input_tokens": inp, "output_tokens": out, "cache_read": cr,
                  "cache_write": cw, "total_tokens": total, "cost_usd": cost},
    }


class TestBuildAggregates(unittest.TestCase):
    def test_gruppiert_und_aggregiert(self):
        results = [
            _res("pi", total=100, cost=0.001),
            _res("pi", total=300, cost=0.003),
        ]
        aggs = stats.build_aggregates(results)
        self.assertEqual(len(aggs), 1)
        a = aggs[0]
        self.assertEqual(a["harness"], "pi")
        self.assertEqual(a["task_id"], "baseline-overhead")
        self.assertEqual(a["n"], 2)
        self.assertEqual(a["metrics"]["total_tokens"]["median"], 200)
        self.assertEqual(a["metrics"]["total_tokens"]["min"], 100)
        self.assertEqual(a["metrics"]["total_tokens"]["max"], 300)

    def test_overhead_metric_ist_input_plus_cache(self):
        results = [_res("pi", inp=500, cr=100, cw=400, out=999)]
        aggs = stats.build_aggregates(results)
        self.assertEqual(aggs[0]["metrics"]["overhead"]["median"], 1000)

    def test_fehler_werden_ausgeschlossen(self):
        results = [
            _res("pi", total=100),
            _res("pi", total=999999, error="kaputt"),
        ]
        aggs = stats.build_aggregates(results)
        self.assertEqual(aggs[0]["n"], 1)
        self.assertEqual(aggs[0]["metrics"]["total_tokens"]["median"], 100)

    def test_trennt_harnesses_und_modelle(self):
        results = [
            _res("pi", model="Haiku 4.5"),
            _res("claude-code", model="Haiku 4.5"),
            _res("pi", model="Sonnet 4.6"),
        ]
        aggs = stats.build_aggregates(results)
        keys = {(a["harness"], a["model_label"]) for a in aggs}
        self.assertEqual(keys, {("pi", "Haiku 4.5"), ("claude-code", "Haiku 4.5"), ("pi", "Sonnet 4.6")})


if __name__ == "__main__":
    unittest.main()
