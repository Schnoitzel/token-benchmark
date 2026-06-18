"""
Modell-Definitionen.

Hier kannst du Modelle hinzufügen oder entfernen – der Benchmark nimmt sie
automatisch auf.

  label      : Anzeigename
  pi_model   : Modell-ID für Pi (--model Flag)
  cc_model   : Modell-Alias/ID für Claude Code (--model Flag)
  tier       : grobe Preisklasse (nur fürs Anzeigen)
"""

from dataclasses import dataclass


@dataclass
class Model:
    label: str
    pi_model: str
    cc_model: str
    tier: str  # "cheap" | "mid" | "expensive"


MODELS: list[Model] = [
    Model(label="Haiku 4.5",  pi_model="claude-haiku-4-5",  cc_model="haiku",  tier="cheap"),
    Model(label="Sonnet 4.6", pi_model="claude-sonnet-4-5", cc_model="sonnet", tier="mid"),
    Model(label="Opus 4.8",   pi_model="claude-opus-4-8",   cc_model="opus",   tier="expensive"),
]
