"""Tests fuer die einheitliche Kostenberechnung (pricing.py).

Reine Logik, keine API-Aufrufe. Die Erwartungswerte sind von Hand nachgerechnet,
damit die Tests die Formel echt absichern (nicht nur das Ergebnis der Funktion
gegen sich selbst pruefen).
"""

import unittest

import pricing
from runners import TokenUsage


class TestComputeCost(unittest.TestCase):
    def test_haiku_alle_kategorien_handberechnet(self):
        # Haiku: input 1.00, output 5.00 USD/MTok; write x1.25, read x0.10
        # (1000*1.00 + 2000*5.00 + 5000*1.00*1.25 + 10000*1.00*0.10) / 1e6
        # = (1000 + 10000 + 6250 + 1000) / 1e6 = 0.01825
        cost = pricing.compute_cost("Haiku 4.5", 1000, 2000, 10000, 5000)
        self.assertAlmostEqual(cost, 0.01825, places=10)

    def test_sonnet_nur_input_output(self):
        # Sonnet: input 3.00, output 15.00
        # (1000*3 + 1000*15) / 1e6 = 0.018
        cost = pricing.compute_cost("Sonnet 4.6", 1000, 1000, 0, 0)
        self.assertAlmostEqual(cost, 0.018, places=10)

    def test_cache_read_ist_billiger_als_cache_write(self):
        # gleiche Tokenzahl: read (x0.10) muss guenstiger sein als write (x1.25)
        read_cost = pricing.compute_cost("Opus 4.8", 0, 0, 1000, 0)
        write_cost = pricing.compute_cost("Opus 4.8", 0, 0, 0, 1000)
        self.assertLess(read_cost, write_cost)

    def test_cache_write_multiplikator(self):
        # Opus input 15.00; write x1.25 -> 1000 * 15 * 1.25 / 1e6 = 0.01875
        cost = pricing.compute_cost("Opus 4.8", 0, 0, 0, 1000)
        self.assertAlmostEqual(cost, 0.01875, places=10)

    def test_cache_read_multiplikator(self):
        # Opus input 15.00; read x0.10 -> 1000 * 15 * 0.10 / 1e6 = 0.0015
        cost = pricing.compute_cost("Opus 4.8", 0, 0, 1000, 0)
        self.assertAlmostEqual(cost, 0.0015, places=10)

    def test_unbekanntes_modell_gibt_none(self):
        self.assertIsNone(pricing.compute_cost("Gibt-es-nicht", 1, 1, 1, 1))

    def test_nullwerte(self):
        self.assertEqual(pricing.compute_cost("Haiku 4.5", 0, 0, 0, 0), 0.0)


class TestCostForUsage(unittest.TestCase):
    def test_mit_dict(self):
        usage = {"input_tokens": 1000, "output_tokens": 1000,
                 "cache_read": 0, "cache_write": 0}
        self.assertAlmostEqual(
            pricing.cost_for_usage("Sonnet 4.6", usage), 0.018, places=10
        )

    def test_mit_tokenusage_objekt(self):
        usage = TokenUsage(input_tokens=1000, output_tokens=1000,
                           cache_read=0, cache_write=0)
        self.assertAlmostEqual(
            pricing.cost_for_usage("Sonnet 4.6", usage), 0.018, places=10
        )

    def test_dict_und_objekt_liefern_gleiches_ergebnis(self):
        d = {"input_tokens": 500, "output_tokens": 700,
             "cache_read": 1200, "cache_write": 300}
        o = TokenUsage(input_tokens=500, output_tokens=700,
                       cache_read=1200, cache_write=300)
        self.assertEqual(
            pricing.cost_for_usage("Haiku 4.5", d),
            pricing.cost_for_usage("Haiku 4.5", o),
        )

    def test_unbekanntes_modell_gibt_none(self):
        self.assertIsNone(pricing.cost_for_usage("Foo", {"input_tokens": 1}))


if __name__ == "__main__":
    unittest.main()
