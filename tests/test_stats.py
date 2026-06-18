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


if __name__ == "__main__":
    unittest.main()
