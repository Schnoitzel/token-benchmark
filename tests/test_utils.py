"""Tests fuer die gemeinsamen Helfer (utils.py).

Konsolidiert vorher duplizierte Funktionen aus report.py/judge.py/main.py.
"""

import json
import os
import tempfile
import unittest

import utils


class TestFmtCost(unittest.TestCase):
    def test_millidollar_unter_grenze(self):
        # < 0.001 USD -> Millidollar mit 4 Nachkommastellen (vereinheitlicht)
        self.assertEqual(utils.fmt_cost(0.0005), "0.5000m$")

    def test_dollar_ueber_grenze(self):
        self.assertEqual(utils.fmt_cost(0.01234), "$0.01234")

    def test_grenze_genau(self):
        # genau 0.001 ist NICHT < 0.001 -> Dollar-Form
        self.assertTrue(utils.fmt_cost(0.001).startswith("$"))


class TestFmtN(unittest.TestCase):
    def test_tausender(self):
        self.assertEqual(utils.fmt_n(12345), "12,345")

    def test_null_und_klein(self):
        self.assertEqual(utils.fmt_n(0), "0")
        self.assertEqual(utils.fmt_n(999), "999")

    def test_rundet(self):
        self.assertEqual(utils.fmt_n(1234.6), "1,235")


class TestRatio(unittest.TestCase):
    def test_groesser(self):
        self.assertEqual(utils.ratio(10, 5), "2.0x")

    def test_kleiner(self):
        self.assertIn("weniger", utils.ratio(5, 10))

    def test_null_gibt_na(self):
        self.assertEqual(utils.ratio(0, 5), "n/a")
        self.assertEqual(utils.ratio(5, 0), "n/a")


class TestOverheadTokens(unittest.TestCase):
    def test_input_plus_cache_ohne_output(self):
        usage = {"input_tokens": 500, "output_tokens": 999,
                 "cache_read": 100, "cache_write": 400}
        # Output zaehlt NICHT zum Overhead
        self.assertEqual(utils.overhead_tokens(usage), 1000)


class TestLoadSuite(unittest.TestCase):
    def _write_suite(self, dirpath, run_id, content=None):
        fp = os.path.join(dirpath, f"benchmark-{run_id}.json")
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(content or {"run_id": run_id, "results": []}, f)
        return fp

    def test_load_suite_liest_datei(self):
        with tempfile.TemporaryDirectory() as tmp:
            fp = self._write_suite(tmp, "abc", {"run_id": "abc", "x": 1})
            suite = utils.load_suite(fp)
            self.assertEqual(suite["run_id"], "abc")
            self.assertEqual(suite["x"], 1)

    def test_latest_suite_path_nimmt_neueste(self):
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                os.makedirs("results", exist_ok=True)
                self._write_suite("results", "aaa11111")
                self._write_suite("results", "zzz99999")
                latest = utils.latest_suite_path()
                # sortiert -> "zzz99999" ist die letzte
                self.assertTrue(latest.endswith("benchmark-zzz99999.json"))
            finally:
                os.chdir(cwd)

    def test_latest_suite_path_ohne_dateien(self):
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                with self.assertRaises(SystemExit):
                    utils.latest_suite_path()
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
