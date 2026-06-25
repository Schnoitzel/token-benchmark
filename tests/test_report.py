"""Tests fuer die Report-Aggregation (report.py).

Reine Logik (Median/Spanne/Verhaeltnis/Overhead), keine Datei-IO noetig.
"""

import unittest

import report


def make_result(harness, model, complexity="baseline", task_id="baseline-overhead",
                inp=0, out=0, cr=0, cw=0, total=None, cost=0.0, dur=1000):
    if total is None:
        total = inp + out + cr + cw
    return {
        "harness": harness,
        "model_label": model,
        "task_id": task_id,
        "task_complexity": complexity,
        "duration_ms": dur,
        "usage": {
            "input_tokens": inp, "output_tokens": out,
            "cache_read": cr, "cache_write": cw,
            "total_tokens": total, "cost_usd": cost,
        },
    }


class TestKleineHelfer(unittest.TestCase):
    def test_med(self):
        self.assertEqual(report.med([3, 1, 2]), 2)
        self.assertEqual(report.med([1, 2, 3, 4]), 2.5)

    def test_med_leer_ist_null(self):
        self.assertEqual(report.med([]), 0.0)

    def test_order_idx(self):
        self.assertEqual(report.order_idx("baseline"), 0)
        self.assertLess(report.order_idx("trivial"), report.order_idx("complex"))
        self.assertEqual(report.order_idx("unbekannt"), len(report.ORDER))

    def test_fmt_cost_milli_und_dollar(self):
        self.assertIn("m$", report.fmt_cost(0.0005))   # < 0.001 -> Millidollar
        self.assertTrue(report.fmt_cost(0.01).startswith("$"))

    def test_fmt_n_tausender(self):
        self.assertEqual(report.fmt_n(12345), "12,345")
        self.assertEqual(report.fmt_n(0), "0")
        self.assertEqual(report.fmt_n(999), "999")
        self.assertEqual(report.fmt_n(1_234_567_890), "1,234,567,890")

    def test_ratio(self):
        self.assertEqual(report.ratio(10, 5), "2.0x")
        self.assertIn("weniger", report.ratio(5, 10))
        self.assertEqual(report.ratio(0, 5), "n/a")
        self.assertEqual(report.ratio(5, 0), "n/a")


class TestMedianUndSpread(unittest.TestCase):
    def test_median_of_verschachtelt(self):
        rows = [make_result("pi", "Haiku 4.5", inp=100),
                make_result("pi", "Haiku 4.5", inp=200),
                make_result("pi", "Haiku 4.5", inp=300)]
        self.assertEqual(report.median_of(rows, "usage", "input_tokens"), 200)

    def test_spread_gibt_median_min_max_n(self):
        rows = [make_result("pi", "Haiku 4.5", total=100),
                make_result("pi", "Haiku 4.5", total=300),
                make_result("pi", "Haiku 4.5", total=200)]
        m, lo, hi, n = report.spread(rows, "usage", "total_tokens")
        self.assertEqual((m, lo, hi, n), (200, 100, 300, 3))

    def test_spread_leer(self):
        self.assertEqual(report.spread([], "usage", "total_tokens"), (0.0, 0.0, 0.0, 0))


class TestOverheadRows(unittest.TestCase):
    def test_bevorzugt_baseline_aufgabe(self):
        results = [
            # Baseline: Pi overhead = 3000, CC overhead = 29000
            make_result("pi", "Haiku 4.5", complexity="baseline", inp=3000),
            make_result("claude-code", "Haiku 4.5", complexity="baseline", inp=10, cr=21000, cw=8000),
            # andere Aufgabe (soll ignoriert werden, da Baseline existiert)
            make_result("pi", "Haiku 4.5", complexity="trivial", task_id="x", inp=99999),
        ]
        baseline = [r for r in results if r["task_complexity"] == "baseline"]
        rows = report._overhead_rows(baseline)
        self.assertEqual(len(rows), 1)
        model, pi_ov, cc_ov = rows[0]
        self.assertEqual(model, "Haiku 4.5")
        self.assertEqual(pi_ov, 3000)
        self.assertEqual(cc_ov, 10 + 21000 + 8000)

    def test_overhead_ist_input_plus_cache(self):
        results = [make_result("pi", "Sonnet 4.6", inp=500, cr=100, cw=400, out=999)]
        rows = report._overhead_rows(results)
        _, pi_ov, _ = rows[0]
        # output (999) zaehlt NICHT zum Overhead
        self.assertEqual(pi_ov, 500 + 100 + 400)

    def test_overhead_stats_mit_streuung(self):
        results = [
            make_result("pi", "Haiku 4.5", inp=3000),
            make_result("pi", "Haiku 4.5", inp=3100),
            make_result("claude-code", "Haiku 4.5", inp=10, cr=21000, cw=8000),
            make_result("claude-code", "Haiku 4.5", inp=10, cr=21000, cw=8200),
        ]
        rows = report._overhead_stats(results)
        self.assertEqual(len(rows), 1)
        model, pi_s, cc_s = rows[0]
        self.assertEqual(pi_s["n"], 2)
        self.assertEqual(pi_s["median"], 3050)
        self.assertEqual(pi_s["min"], 3000)
        self.assertEqual(pi_s["max"], 3100)
        self.assertGreater(cc_s["median"], pi_s["median"] * 6)

    def test_cell_stat_format(self):
        s = {"median": 3050, "min": 3000, "max": 3100, "n": 2}
        self.assertEqual(report._cell_stat(s), "3,050 (3,000–3,100, n=2)")

    def test_fallback_ohne_baseline(self):
        # keine baseline-Task vorhanden -> nutzt alle Ergebnisse statt leer
        results = [
            make_result("pi", "Haiku 4.5", complexity="trivial", task_id="t", inp=200),
            make_result("claude-code", "Haiku 4.5", complexity="trivial", task_id="t", inp=10, cr=2000, cw=500),
        ]
        rows = report._overhead_rows(results)
        self.assertEqual(len(rows), 1)
        model, pi_ov, cc_ov = rows[0]
        self.assertEqual(pi_ov, 200)
        self.assertEqual(cc_ov, 10 + 2000 + 500)


class TestMarkdownBreakdown(unittest.TestCase):
    """Phase B: Markdown-Tabelle zeigt Streuung fuer alle Token-Felder + Overhead-Spalte."""

    def _make_suite(self):
        """Mini-Suite mit 2 Wiederholungen (Baseline, Haiku, Pi + CC)."""
        results = [
            make_result("pi", "Haiku 4.5", inp=3070, out=4,  cr=0,     cw=0,    cost=0.003),
            make_result("pi", "Haiku 4.5", inp=3068, out=4,  cr=0,     cw=0,    cost=0.003),
            make_result("claude-code", "Haiku 4.5", inp=10,   out=43, cr=21506, cw=7778, cost=0.012),
            make_result("claude-code", "Haiku 4.5", inp=10,   out=43, cr=21506, cw=7780, cost=0.012),
        ]
        for i, r in enumerate(results):
            r["repeat_index"] = i % 2
            r["task_prompt"] = "Reply with exactly: OK"
            r["response"] = "OK"
            r["timestamp"] = "2026-06-25T00:00:00+00:00"
        return {
            "run_id": "test1234",
            "started_at": "2026-06-25T00:00:00+00:00",
            "finished_at": "2026-06-25T00:01:00+00:00",
            "results": results,
            "aggregates": [],
            "provenance": {"repeat": 2},
        }

    def test_markdown_enthaelt_overhead_spalte(self):
        md = report.build_markdown(self._make_suite())
        self.assertIn("Overhead", md)

    def test_markdown_enthaelt_cache_write_spalte(self):
        md = report.build_markdown(self._make_suite())
        # Cache-Write-Spalte muss als eigene Spalte im Header stehen
        self.assertIn("cache↑W", md)

    def test_markdown_zeigt_streuung_fuer_input(self):
        md = report.build_markdown(self._make_suite())
        # Input Pi: Median=3069, min=3068, max=3070 -> muss min-max zeigen
        self.assertIn("3,068", md)
        self.assertIn("3,070", md)

    def test_markdown_zeigt_streuung_fuer_cache_write(self):
        md = report.build_markdown(self._make_suite())
        # CC cache_write: 7778 und 7780 -> beide muessen auftauchen
        self.assertIn("7,778", md)
        self.assertIn("7,780", md)

    def test_overhead_wert_korrekt_berechnet(self):
        md = report.build_markdown(self._make_suite())
        # Pi Overhead = input(3069 Median) + cr(0) + cw(0) = 3069
        # CC Overhead = input(10) + cr(21506) + cw(7779 Median) = 29295
        self.assertIn("3,069", md)
        self.assertIn("29,295", md)


if __name__ == "__main__":
    unittest.main()
