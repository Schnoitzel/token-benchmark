"""REALER Mess-Test (opt-in) - ruft pi und claude WIRKLICH auf.

Dieser Test trifft eine belastbare Aussage ueber den tatsaechlichen
Token-Overhead. Er kostet Tokens/Geld und braucht pi+claude im PATH mit
gueltigem Login. Deshalb ist er standardmaessig UEBERSPRUNGEN und laeuft nur
mit gesetzter Umgebungsvariable:

    RUN_LIVE=1 python3 -m unittest tests.test_live_measurement

Er prueft NICHT exakte Festwerte (Modelle/Versionen aendern sich), sondern:
  1. Plausibilitaet: CC-Overhead ist um ein Vielfaches groesser als Pi.
  2. Reproduzierbarkeit: die relative Streuung ueber Wiederholungen ist klein.
"""

import os
import unittest

import stats
from models import MODELS
from runners import run_pi, run_claude
from tasks import TASKS

REPEATS = 3  # bewusst klein -> wenig Kosten, reicht fuer Streuungs-Aussage


def _baseline_task():
    return next(t for t in TASKS if t.id == "baseline-overhead")


def _haiku():
    return next(m for m in MODELS if m.label == "Haiku 4.5")


def _overhead(usage):
    return usage.input_tokens + usage.cache_read + usage.cache_write


@unittest.skipUnless(os.environ.get("RUN_LIVE"), "Realer Mess-Test: nur mit RUN_LIVE=1")
class TestLiveOverhead(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        task, model = _baseline_task(), _haiku()
        cls.pi_ov, cls.cc_ov = [], []
        for _ in range(REPEATS):
            try:
                pi = run_pi(task, model)
                cc = run_claude(task, model)
            except Exception as e:  # Tool nicht im PATH o.ae.
                raise unittest.SkipTest(f"pi/claude nicht ausfuehrbar: {e}")
            if pi.error or cc.error:
                raise unittest.SkipTest(
                    f"Harness nicht verfuegbar/eingeloggt (pi={pi.error}, cc={cc.error})"
                )
            cls.pi_ov.append(_overhead(pi.usage))
            cls.cc_ov.append(_overhead(cc.usage))

    def test_cc_overhead_vielfaches_von_pi(self):
        pi_med = stats.median(self.pi_ov)
        cc_med = stats.median(self.cc_ov)
        self.assertGreater(pi_med, 0)
        # erwartet ~9-10x; konservativ >5x, damit der Test robust gegen
        # Versions-/Modell-Schwankungen bleibt, aber die Aussage absichert
        self.assertGreater(cc_med, pi_med * 5,
                           f"CC-Overhead {cc_med} nicht >5x Pi {pi_med}")

    def test_pi_overhead_reproduzierbar(self):
        # blanke Pi-Laeufe sind extrem stabil -> rel. Streuung < 5%
        self.assertLess(stats.rel_spread(self.pi_ov), 0.05,
                        f"Pi-Overhead schwankt zu stark: {self.pi_ov}")

    def test_cc_overhead_reproduzierbar(self):
        self.assertLess(stats.rel_spread(self.cc_ov), 0.10,
                        f"CC-Overhead schwankt zu stark: {self.cc_ov}")


if __name__ == "__main__":
    unittest.main()
