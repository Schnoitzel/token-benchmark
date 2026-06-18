"""Tests fuer die testbare Server-Logik (server.py).

Wir testen build_config() direkt (ohne echten HTTP-Server) - so kann die UI
Preise/Cache-Faktoren aus EINER Quelle (pricing.py) laden, statt sie im
Frontend hartzukodieren.
"""

import unittest

import pricing
import server


class TestBuildConfig(unittest.TestCase):
    def setUp(self):
        self.cfg = server.build_config()

    def test_enthaelt_modelle_und_tasks(self):
        self.assertTrue(self.cfg["models"])
        self.assertTrue(self.cfg["tasks"])
        self.assertIn("label", self.cfg["models"][0])
        self.assertIn("id", self.cfg["tasks"][0])

    def test_enthaelt_preise_aus_pricing(self):
        prices = self.cfg["pricing"]["models"]
        # jedes bepreiste Modell aus pricing.py taucht auf
        for label, (inp, out) in pricing.PRICES.items():
            self.assertIn(label, prices)
            self.assertEqual(prices[label]["input"], inp)
            self.assertEqual(prices[label]["output"], out)

    def test_enthaelt_cache_faktoren(self):
        cm = self.cfg["pricing"]["cache_multipliers"]
        self.assertEqual(cm["write"], pricing.CACHE_WRITE_MULT)
        self.assertEqual(cm["read"], pricing.CACHE_READ_MULT)


if __name__ == "__main__":
    unittest.main()
