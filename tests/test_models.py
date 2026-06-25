"""
Tests fuer models.py:
- Pi-Modell-IDs sind nicht leer und unterscheiden sich von CC-Alias
- Bekannte Pi-Modell-IDs (aus `pi --list-models` verifiziert, 2026-06-25)
- Labels eindeutig
"""
import unittest
from models import MODELS

# Verifizierte Pi-Modell-IDs (Stand 2026-06-25, aus `pi --list-models`)
KNOWN_PI_IDS = {
    "claude-haiku-4-5",
    "claude-sonnet-4-6",
    "claude-opus-4-8",
}


class TestModels(unittest.TestCase):

    def test_no_empty_fields(self):
        for m in MODELS:
            self.assertTrue(m.label,    f"label leer: {m}")
            self.assertTrue(m.pi_model, f"pi_model leer: {m}")
            self.assertTrue(m.cc_model, f"cc_model leer: {m}")
            self.assertTrue(m.tier,     f"tier leer: {m}")

    def test_pi_model_differs_from_cc_model(self):
        """Pi-IDs sind vollstaendige Modell-Namen, CC nutzt Kurzaliase."""
        for m in MODELS:
            self.assertNotEqual(
                m.pi_model, m.cc_model,
                f"{m.label}: pi_model == cc_model (beide '{m.pi_model}')",
            )

    def test_pi_models_in_known_allowlist(self):
        """Stellt sicher dass keine veraltete oder falsche ID verwendet wird."""
        for m in MODELS:
            self.assertIn(
                m.pi_model, KNOWN_PI_IDS,
                f"{m.label}: pi_model '{m.pi_model}' nicht in verifizierter Allowlist {KNOWN_PI_IDS}",
            )

    def test_labels_unique(self):
        labels = [m.label for m in MODELS]
        self.assertEqual(len(labels), len(set(labels)), "Doppelte Labels gefunden")

    def test_pi_model_ids_unique(self):
        ids = [m.pi_model for m in MODELS]
        self.assertEqual(len(ids), len(set(ids)), "Doppelte pi_model-IDs gefunden")


if __name__ == "__main__":
    unittest.main()
