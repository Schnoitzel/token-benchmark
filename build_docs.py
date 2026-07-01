#!/usr/bin/env python3
"""
Erzeugt zwei Dokumentations-PDFs:
  docs/pdf/token-benchmark-methodik-ergebnisse.pdf   (PDF 1: Beleg)
  docs/pdf/token-benchmark-nutzung-ausblick.pdf       (PDF 2: Anleitung)

Verwendung:
  python3 build_docs.py             # beide PDFs
  python3 build_docs.py --pdf1      # nur PDF 1
  python3 build_docs.py --pdf2      # nur PDF 2

Erfordert: pip install fpdf2
Datenquelle: results/benchmark-9a72151a.json
"""

import json
import sys
from pathlib import Path
from fpdf import FPDF, XPos, YPos

# ---------------------------------------------------------------------------
# Konstanten & Farben
# ---------------------------------------------------------------------------
SUITE_PATH = Path("results/benchmark-9a72151a.json")
OUT_DIR    = Path("docs/pdf")

# SelectLine-Farbpalette
C_ANTHRAZIT = (0x1F, 0x33, 0x40)   # #1F3340 — Überschriften
C_ORANGE    = (0xFF, 0x6C, 0x2F)   # #FF6C2F — Akzente / Trennlinien
C_WHITE     = (0xFF, 0xFF, 0xFF)
C_LIGHT     = (0xF4, 0xF6, 0xF8)   # Tabellen-Zebrafarbe
C_DARK      = (0x2C, 0x2C, 0x2C)   # Fließtext

DATUM      = "Juli 2026"
VERSION    = "benchmark-9a72151a"

# ---------------------------------------------------------------------------
# Daten laden
# ---------------------------------------------------------------------------
def load_data():
    with open(SUITE_PATH) as f:
        d = json.load(f)
    # Aggregates: Liste → Dict (task_id, model_label, harness) → metrics
    agg_idx = {}
    for a in d.get("aggregates", []):
        key = (a["task_id"], a["model_label"], a["harness"])
        agg_idx[key] = a["metrics"]
    return d, agg_idx


def agg_val(agg_idx, task, model, harness, metric, stat="median"):
    m = agg_idx.get((task, model, harness), {}).get(metric, {})
    return m.get(stat, 0) if m else 0


# Pfade zu Unicode-Fonts (DejaVu, auf dem System verfuegbar)
FONT_DIR  = "/usr/share/fonts/truetype/dejavu"
FONT_MONO_DIR = "/usr/share/fonts/truetype/dejavu"

# ---------------------------------------------------------------------------
# Basis-PDF-Klasse
# ---------------------------------------------------------------------------
class DocPDF(FPDF):
    def __init__(self, title):
        super().__init__("P", "mm", "A4")
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(15, 15, 15)
        self._doc_title = title
        self._current_section = ""
        # Unicode-Fonts laden (DejaVu = vollstaendiger Unicode-Support)
        self.add_font("Sans",   "",  f"{FONT_DIR}/DejaVuSans.ttf")
        self.add_font("Sans",   "B", f"{FONT_DIR}/DejaVuSans-Bold.ttf")
        self.add_font("Sans",   "I", f"{FONT_DIR}/DejaVuSans.ttf")   # kein Italic vorhanden -> Regular
        self.add_font("Sans",   "BI",f"{FONT_DIR}/DejaVuSans-Bold.ttf")
        self.add_font("Mono",   "",  f"{FONT_MONO_DIR}/DejaVuSansMono.ttf")
        self.add_font("Mono",   "B", f"{FONT_MONO_DIR}/DejaVuSansMono-Bold.ttf")

    # ---- Farb-Helfer ----
    def set_fill_rgb(self, rgb):
        self.set_fill_color(*rgb)

    def set_text_rgb(self, rgb):
        self.set_text_color(*rgb)

    def set_draw_rgb(self, rgb):
        self.set_draw_color(*rgb)

    # ---- Kopf- / Fußzeile ----
    def header(self):
        if self.page_no() == 1:
            return
        # Orangefarbene Trennlinie oben
        self.set_draw_rgb(C_ORANGE)
        self.set_line_width(0.5)
        self.line(15, 12, 195, 12)
        self.set_font("Sans", "I", 8)
        self.set_text_rgb((0xAA, 0xAA, 0xAA))
        self.set_xy(15, 7)
        self.cell(0, 5, self._doc_title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_rgb(C_DARK)

    def footer(self):
        self.set_y(-12)
        self.set_draw_rgb(C_ORANGE)
        self.set_line_width(0.3)
        self.line(15, self.get_y(), 195, self.get_y())
        self.set_font("Sans", "I", 8)
        self.set_text_rgb((0xAA, 0xAA, 0xAA))
        self.cell(0, 8, f"Seite {self.page_no()}  |  SelectLine Software AG  |  {DATUM}",
                  align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_rgb(C_DARK)

    # ---- Titelseite ----
    def title_page(self, subtitle, version_line=""):
        self.add_page()
        # Hintergrundbalken
        self.set_fill_rgb(C_ANTHRAZIT)
        self.rect(0, 0, 210, 80, "F")
        # Orangefarbener Akzentbalken
        self.set_fill_rgb(C_ORANGE)
        self.rect(0, 80, 210, 4, "F")

        # Titel
        self.set_font("Sans", "B", 28)
        self.set_text_rgb(C_WHITE)
        self.set_xy(15, 20)
        self.multi_cell(180, 10, self._doc_title)

        # Subtitle
        self.set_font("Sans", "", 14)
        self.set_text_rgb((0xCC, 0xCC, 0xCC))
        self.set_xy(15, 55)
        self.cell(0, 8, subtitle, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Meta-Block
        self.set_fill_rgb(C_LIGHT)
        self.rect(15, 95, 180, 38, "F")
        self.set_font("Sans", "", 10)
        self.set_text_rgb(C_DARK)
        self.set_xy(20, 100)
        lines = [
            f"Datenquelle: {VERSION}.json",
            f"Datum: {DATUM}",
            f"Runs: 540 (n=10 je Kombination, ausser Real-Task n=5)",
            f"Harnesses: Pi 0.80.2  |  Claude Code 2.1.170 / 2.1.196",
        ]
        if version_line:
            lines.append(version_line)
        for line in lines:
            self.set_x(20)
            self.cell(0, 6, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ---- Abschnittsüberschrift ----
    def section(self, title, level=1):
        self._current_section = title
        # Überschrift nicht am Seitenende verwaisen lassen
        self.check_pb(26 if level == 1 else 20)
        if level == 1:
            self.ln(2)
            self.set_font("Sans", "B", 14)
            self.set_text_rgb(C_ANTHRAZIT)
            self.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_draw_rgb(C_ORANGE)
            self.set_line_width(0.6)
            x = self.get_x()
            y = self.get_y()
            self.line(x, y, 195, y)
            self.ln(2)
        else:
            self.ln(2)
            self.set_font("Sans", "B", 11)
            self.set_text_rgb(C_ANTHRAZIT)
            self.cell(0, 6, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(1)
        self.set_text_rgb(C_DARK)
        self.set_font("Sans", "", 10)

    # ---- Absatz ----
    def para(self, text, indent=0):
        self.set_font("Sans", "", 10)
        self.set_text_rgb(C_DARK)
        self.set_x(15 + indent)
        self.multi_cell(180 - indent, 5.5, text)
        # multi_cell lässt den Cursor am rechten Rand -> zurück an den linken Rand,
        # sonst startet ein folgender cell()/table_header() außerhalb des Rahmens
        self.set_x(self.l_margin)

    # ---- Aufzählung ----
    def bullet(self, items, indent=4):
        self.set_font("Sans", "", 10)
        self.set_text_rgb(C_DARK)
        for item in items:
            self.set_x(15 + indent)
            self.cell(5, 5.5, "\u2022")
            self.set_x(20 + indent)
            self.multi_cell(175 - indent, 5.5, item)
        self.set_x(self.l_margin)  # Cursor zurück an den linken Rand

    # ---- Code-Block ----
    def code_block(self, text):
        self.set_font("Mono", "", 9)
        self.set_fill_rgb(C_LIGHT)
        self.set_text_rgb(C_ANTHRAZIT)
        self.set_x(15)
        lines = text.strip().split("\n")
        for line in lines:
            self.set_x(17)
            self.cell(176, 5.5, line, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)
        self.set_font("Sans", "", 10)
        self.set_text_rgb(C_DARK)

    # ---- Tabellen-Helfer ----
    def table_header(self, cols, widths, bg=C_ANTHRAZIT):
        """Einzeilige Header-Zeile."""
        # Kopfzeile nie am Seitenende verwaisen lassen und immer am linken Rand starten
        self.check_pb(22)
        self.set_x(self.l_margin)
        self.set_font("Sans", "B", 9)
        self.set_fill_rgb(bg)
        self.set_text_rgb(C_WHITE)
        self.set_draw_color(200, 200, 200)
        for col, w in zip(cols, widths):
            self.cell(w, 7, col, border=1, fill=True, align="C")
        self.ln()
        self.set_text_rgb(C_DARK)
        self.set_font("Sans", "", 9)

    def table_row(self, values, widths, aligns=None, zebra=False, bold_cols=None,
                  repeat_header=None):
        """Einzeilige Tabellen-Zeile."""
        if aligns is None:
            aligns = ["L"] * len(values)
        if bold_cols is None:
            bold_cols = []
        # Seitenumbruch vor der Zeile; Kopfzeile auf neuer Seite ggf. wiederholen
        pg = self.page_no()
        self.check_pb(8)
        if repeat_header and self.page_no() != pg:
            self.table_header(*repeat_header)
        self.set_x(self.l_margin)
        if zebra:
            self.set_fill_rgb(C_LIGHT)
        else:
            self.set_fill_rgb(C_WHITE)
        self.set_draw_color(200, 200, 200)
        for i, (val, w, align) in enumerate(zip(values, widths, aligns)):
            self.set_font("Sans", "B" if i in bold_cols else "", 9)
            self.cell(w, 6.5, str(val), border=1, fill=True, align=align)
        self.ln()
        self.set_font("Sans", "", 9)

    def table_row_wrap(self, values, widths, aligns=None, zebra=False,
                       bold_cols=None, line_h=5.0, repeat_header=None):
        """Tabellen-Zeile mit Zeilenumbruch in langen Textzellen."""
        if aligns is None:
            aligns = ["L"] * len(values)
        if bold_cols is None:
            bold_cols = []

        # Zeilenhoehe berechnen: Schätzung basierend auf Textlaenge je Zelle
        def est_lines(text, w):
            chars_per_line = max(1, int((w - 2) / 2.1))  # ~2,1mm pro Zeichen bei 9pt
            hard_lines = text.split("\n")
            total = 0
            for seg in hard_lines:
                total += max(1, (len(seg) + chars_per_line - 1) // chars_per_line)
            return total

        row_h = max(est_lines(str(v), w) for v, w in zip(values, widths)) * line_h + 1
        row_h = max(row_h, line_h + 1)  # Mindesthoehe

        # Seitenumbruch VOR der (evtl. hohen) Zeile; Kopfzeile ggf. wiederholen
        pg = self.page_no()
        self.check_pb(row_h + 2)
        if repeat_header and self.page_no() != pg:
            self.table_header(*repeat_header)
        self.set_x(self.l_margin)

        self.set_draw_color(200, 200, 200)
        fill_color = C_LIGHT if zebra else C_WHITE
        self.set_fill_rgb(fill_color)

        x0, y0 = self.get_x(), self.get_y()

        # 1. Pass: gefuellte Hintergrund-Rechtecke mit korrekter Gesamthoehe
        for w in widths:
            self.cell(w, row_h, "", border=1, fill=True)

        # 2. Pass: Text in jede Zelle (multi_cell fuer Umbruch)
        x_cur = x0
        for i, (val, w, align) in enumerate(zip(values, widths, aligns)):
            self.set_font("Sans", "B" if i in bold_cols else "", 9)
            self.set_xy(x_cur + 1, y0 + 0.8)
            self.multi_cell(w - 2, line_h, str(val), align=align)
            x_cur += w

        # Y auf naechste Zeile setzen
        self.set_xy(x0, y0 + row_h)
        self.set_font("Sans", "", 9)

    def check_pb(self, h=20):
        """Seite umbrechen wenn zu wenig Platz."""
        if self.get_y() + h > self.page_break_trigger:
            self.add_page()


# ---------------------------------------------------------------------------
# PDF 1: Methodik & Ergebnisse
# ---------------------------------------------------------------------------
def build_pdf1(d, agg_idx):
    pdf = DocPDF("Token-Benchmark: Methodik & Ergebnisse")
    pdf.title_page(
        "Vollständiger Beleg — Versuchsaufbau, Methodik, Tabellen, Qualität",
        "Internes Dokument · SelectLine Software AG"
    )

    # ------------------------------------------------------------------
    # 1. Kurzzusammenfassung
    # ------------------------------------------------------------------
    pdf.add_page()
    pdf.section("1  Kurzzusammenfassung")
    pdf.para(
        "Dieser POC vergleicht zwei KI-Coding-Harnesses — Pi (minimalistisch) und "
        "Claude Code (feature-reich) — bei identischen Prompts und Modellen. "
        "Gemessen werden Token-Verbrauch, Kosten und Antwortqualität."
    )
    pdf.para("Die drei belastbarsten Befunde:")
    pdf.bullet([
        "Token-Overhead: Claude Code sendet ~8× mehr Tokens pro Anfrage als Pi "
        "(~29 000 vs. ~3 500 Tokens), unabhängig vom gewählten Modell.",
        "Kostenoverhead: Wegen günstigem Cache-Read ist der Kosten-Faktor kleiner: "
        "~4–5× (nicht 8×). Tokens zeigen den Umfang, Kosten den finanziellen Effekt.",
        "Qualität: Kein bedeutsamer Unterschied. Blindtest (27 Paare, Richter Opus 4.8): "
        "Pi 3 Siege / CC 13 / 11 Unentschieden. Beide Ø > 4,3 auf einer 5-Punkte-Skala."
    ])
    pdf.para(
        "Robuster Befund: Die Overhead-Kernzahl (~8× Tokens) basiert ausschließlich auf "
        "Single-Turn-Tasks (n=10 je Kombination) und ist OS-unabhängig. Tool-Tasks "
        "(medium-bash) wurden fair im Container gemessen (beide Harnesses nativ Linux)."
    )

    # ------------------------------------------------------------------
    # 2. Versuchsaufbau
    # ------------------------------------------------------------------
    pdf.section("2  Versuchsaufbau")
    pdf.para(
        "Versuchsmatrix: 2 Harnesses × 3 Modelle × 9 synthetische Tasks + 1 Real-Task."
    )
    pdf.bullet([
        "Harnesses: Pi 0.80.2 (minimalistisch) und Claude Code 2.1.170/2.1.196 (feature-reich)",
        "Modelle: Haiku 4.5, Sonnet 4.6, Opus 4.8 (identische Anthropic-Modelle in beiden Harnesses)",
        "Wiederholungen: n=10 je Kombination (Real-Task n=5)",
        "Sandbox: leeres temporäres Arbeitsverzeichnis, kein Projektkontext",
        "Kosten: einheitlich aus Tokens via pricing.py berechnet (eine Preistabelle für beide)",
    ])

    pdf.section("Modell-IDs (verifiziert)", level=2)
    cols = ["Label", "Pi --model", "Claude Code --model"]
    widths = [45, 65, 65]
    pdf.table_header(cols, widths)
    rows = [
        ("Haiku 4.5",  "claude-haiku-4-5",   "haiku"),
        ("Sonnet 4.6", "claude-sonnet-4-6",   "sonnet"),
        ("Opus 4.8",   "claude-opus-4-8",     "opus"),
    ]
    for i, r in enumerate(rows):
        pdf.table_row(r, widths, ["L","L","L"], zebra=(i % 2 == 0))
    pdf.ln(1)

    pdf.section("Preise (Stand Juni 2026)", level=2)
    pdf.para("Alle Kosten einheitlich berechnet aus: input × Preis + cache_read × 0,10 × Preis + "
             "cache_write × 1,25 × Preis + output × Output-Preis.")
    cols = ["Modell", "Input ($/MTok)", "Output ($/MTok)", "Cache-Read", "Cache-Write"]
    widths = [36, 36, 36, 36, 36]
    pdf.table_header(cols, widths)
    price_rows = [
        ("Haiku 4.5",  "$1,00",  "$5,00",  "$0,10",  "$1,25"),
        ("Sonnet 4.6", "$3,00",  "$15,00", "$0,30",  "$3,75"),
        ("Opus 4.8",   "$15,00", "$75,00", "$1,50",  "$18,75"),
    ]
    for i, r in enumerate(price_rows):
        pdf.table_row(r, widths, ["L","R","R","R","R"], zebra=(i % 2 == 0))
    pdf.ln(1)

    # ------------------------------------------------------------------
    # 3. Methodik
    # ------------------------------------------------------------------
    pdf.section("3  Methodik")

    pdf.section("Token-Felder", level=2)
    pdf.para("Jede API-Antwort enthält folgende Token-Felder:")
    cols = ["Feld", "Bedeutung"]
    widths = [35, 145]
    pdf.table_header(cols, widths)
    field_rows = [
        ("input",       "Nicht-gecachte Eingabe-Tokens (User-Nachricht + ggf. ungecachter System-Prompt)"),
        ("cache_read",  "Aus dem Anthropic-Prompt-Cache gelesene Tokens (günstig: 0,10× Input-Preis)"),
        ("cache_write", "In den Cache geschriebene Tokens (1,25× Input-Preis)"),
        ("output",      "Vom Modell erzeugte Antwort-Tokens"),
        ("overhead",    "KERNKENNZAHL: input + cache_read + cache_write — gesamter mitgeschickter Kontext"),
    ]
    for i, r in enumerate(field_rows):
        pdf.table_row(r, widths, ["L","L"], zebra=(i % 2 == 0),
                      bold_cols=[0], repeat_header=(cols, widths))
    pdf.ln(1)

    pdf.section("Verwendete Flags", level=2)
    pdf.para("Pi:")
    pdf.code_block("pi -p --mode json --no-session --no-context-files --no-prompt-templates --thinking off --model <id>")
    pdf.para("Claude Code:")
    pdf.code_block("claude -p --output-format json --model <id> --allow-dangerously-skip-permissions")

    pdf.section("Overhead-Definition & Baseline-Task", level=2)
    pdf.para(
        "Der Harness-Overhead = input + cache_read + cache_write. Das ist der gesamte "
        "pro Anfrage mitgeschickte Kontext ohne die Antwort. "
        "Beim Task 'baseline-overhead' (Prompt: 'Reply with exactly: OK') ist dieser Wert "
        "praktisch identisch mit dem System-Prompt + Tool-Definitionen — der eigentliche "
        "Nutzungsanteil ist minimal."
    )

    pdf.section("Pi turn_end-Summierung (multi-turn)", level=2)
    pdf.para(
        "Pi meldet Tokens pro Turn, nicht kumulativ. Bei Tool-Runs werden alle "
        "turn_end-Events summiert (ADR-0002). Nur das letzte turn_end zu lesen "
        "liefert zu niedrige (falsche) Zahlen."
    )

    # ------------------------------------------------------------------
    # 4. Verifizierte Cache-Semantik
    # ------------------------------------------------------------------
    pdf.section("4  Verifizierte Cache-Semantik")
    pdf.para(
        "Beobachtet in Referenzlauf dcf6c6db (Rohdaten: docs/evidence/), "
        "bestätigt in benchmark-9a72151a.json."
    )

    pdf.section("Pi: modellabhängiges Caching (ADR-0001)", level=2)
    cols = ["Modell", "run#0 (kalt)", "run#1+ (warm)", "Overhead (stabil)"]
    widths = [35, 55, 55, 35]
    pdf.table_header(cols, widths)
    cache_rows = [
        ("Haiku 4.5",  "input≈3070, cache=0",        "input≈3068, cache=0",          "~3.069"),
        ("Sonnet 4.6", "cache_write≈3066, input=3",  "cache_read≈1870 + write≈1196", "~3.069"),
        ("Opus 4.8",   "cache_write≈3784, input=2",  "cache_read≈2504 + write≈1280", "~3.786"),
    ]
    for i, r in enumerate(cache_rows):
        pdf.table_row(r, widths, ["L","L","L","R"], zebra=(i % 2 == 0),
                      bold_cols=[0], repeat_header=(cols, widths))
    pdf.ln(1)
    pdf.para(
        "Wichtig: Der Token-Overhead ist kalt/warm-stabil. Nur die Kosten variieren "
        "(Pi Sonnet kalt ~$0,012 vs. warm ~$0,005 — Faktor ~2,3×)."
    )

    pdf.section("Claude Code: konsistentes Caching", level=2)
    pdf.para(
        "CC nutzt server-seitiges Prompt-Caching konsistent über alle Modelle. "
        "Gesamtoverhead ~27–29k Tokens, aufgeteilt in:"
    )
    pdf.bullet([
        "cache_read ≈ 20.900–21.500 Tokens (stabiler Kern, bei run#0 bereits gecacht — "
        "möglicherweise Anthropic-seitig persistent für CC als offizielles Tool)",
        "cache_write ≈ 3.800–7.800 Tokens (session-spezifischer dynamischer Teil)",
        "input ≈ 10 Tokens (Nachrichten-Boundary)",
    ])

    # ------------------------------------------------------------------
    # 5. Task-Übersicht
    # ------------------------------------------------------------------
    pdf.section("5  Task-Übersicht (alle Prompts)")
    pdf.para(
        "Alle 9 synthetischen Tasks laufen in einer leeren Sandbox (tempfile.TemporaryDirectory). "
        "Keine Pfad-Abhängigkeiten. Der Real-Task läuft direkt im echten JavaFX-Repo."
    )

    from tasks import TASKS
    tasks_by_complexity = {}
    for t in TASKS:
        tasks_by_complexity.setdefault(t.complexity, []).append(t)

    for complexity in ["baseline", "trivial", "simple", "medium", "complex", "real"]:
        if complexity not in tasks_by_complexity:
            continue
        label = {
            "baseline": "Baseline (Overhead-Messung)",
            "trivial":  "Trivial (Wissen / Fakten)",
            "simple":   "Simple (Code / Erklären)",
            "medium":   "Medium (Design / Tool-Nutzung)",
            "complex":  "Complex (Analyse / Refactoring)",
            "real":     "Real-Task (echtes JavaFX-Repo, n=5)",
        }[complexity]
        # Unterüberschrift zusammen mit dem ersten Task halten (kein verwaister Titel)
        first = tasks_by_complexity[complexity][0]
        first_h = (first.prompt.count('\n') + len(first.prompt) // 70 + 2) * 5.5 + 14
        pdf.check_pb(min(first_h + 14, 90))
        pdf.section(label, level=2)
        for t in tasks_by_complexity[complexity]:
            # Hoehe schaetzen: Zeilenumbrueche + Wraps bei ~70 Zeichen pro Zeile
            n_hard = t.prompt.count('\n')
            n_wrap = len(t.prompt) // 70
            est_h  = (n_hard + n_wrap + 2) * 5.5 + 14  # + Header-Zeile
            pdf.check_pb(min(est_h, 80))  # mind. so viel Platz, max 80mm forciert
            pdf.set_font("Sans", "B", 9)
            pdf.set_text_rgb(C_ANTHRAZIT)
            pdf.cell(0, 5, f"[{t.id}]  use_tools={'Ja' if getattr(t, 'use_tools', False) else 'Nein'}  "
                            f"num_turns={getattr(t, 'num_turns', 1)}",
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Sans", "", 9)
            pdf.set_text_rgb(C_DARK)
            # Vollstaendiger Prompt (kein Limit)
            pdf.set_fill_rgb(C_LIGHT)
            pdf.set_x(15)
            pdf.multi_cell(180, 5, t.prompt, fill=True)
            pdf.ln(2)

    # ------------------------------------------------------------------
    # 6. Ergebnisse: Overhead-Kernzahl (Baseline)
    # ------------------------------------------------------------------
    pdf.section("6  Ergebnisse: Overhead-Kernzahl (Baseline)")
    pdf.para(
        "Task: baseline-overhead · n=10 je Kombination · Datenquelle: benchmark-9a72151a.json. "
        "Overhead = input + cache_read + cache_write."
    )

    models = ["Haiku 4.5", "Sonnet 4.6", "Opus 4.8"]
    cols = ["Modell", "Pi Tok. (med)", "CC Tok. (med)", "Fakt.Tok", "Pi $ (med)", "CC $ (med)", "Fakt.$"]
    widths = [30, 28, 28, 18, 26, 26, 24]
    pdf.table_header(cols, widths)
    for i, m in enumerate(models):
        pi_oh  = agg_val(agg_idx, "baseline-overhead", m, "pi",           "overhead")
        cc_oh  = agg_val(agg_idx, "baseline-overhead", m, "claude-code",  "overhead")
        pi_c   = agg_val(agg_idx, "baseline-overhead", m, "pi",           "cost_usd")
        cc_c   = agg_val(agg_idx, "baseline-overhead", m, "claude-code",  "cost_usd")
        f_tok  = f"{cc_oh / pi_oh:.1f}x"  if pi_oh  else "—"
        f_cost = f"{cc_c  / pi_c :.1f}x"  if pi_c   else "—"
        pdf.table_row([
            m,
            f"{pi_oh:,.0f}",
            f"{cc_oh:,.0f}",
            f_tok,
            f"${pi_c:.4f}",
            f"${cc_c:.4f}",
            f_cost,
        ], widths, ["L","R","R","C","R","R","C"], zebra=(i % 2 == 0), bold_cols=[3, 6])
    pdf.ln(1)
    pdf.para(
        "Interpretation: CC schickt ~8× mehr Overhead-Tokens pro Anfrage als Pi — "
        "unabhängig vom Modell. Der Kosten-Faktor ist kleiner (~4–5×), weil der "
        "Großteil des CC-Overheads aus günstigem cache_read besteht (0,10× Input-Preis)."
    )

    # ------------------------------------------------------------------
    # 7. Ergebnisse: Token-Overhead alle Tasks
    # ------------------------------------------------------------------
    pdf.section("7  Ergebnisse: Token-Overhead — alle Tasks")
    pdf.para(
        "Median-Overhead (Tokens) je Task × Modell × Harness. "
        "Synthetische Tasks n=10, Real-Task n=5 (mit Vorbehalt, siehe Abschnitt 11)."
    )

    all_tasks = [
        ("baseline-overhead", "Baseline",  "baseline"),
        ("trivial-fact",      "Fakt",       "trivial"),
        ("trivial-math",      "Mathe",      "trivial"),
        ("simple-code",       "Code",       "simple"),
        ("simple-explain",    "Erklären",   "simple"),
        ("medium-design",     "Design",     "medium"),
        ("medium-bash",       "Bash*",      "medium"),
        ("complex-refactor",  "Refactor",   "complex"),
        ("complex-analysis",  "Analyse",    "complex"),
    ]

    cols = ["Task", "Kompl.", "Modell", "Pi (Tok)", "CC (Tok)", "Faktor"]
    widths = [38, 20, 25, 30, 30, 22]
    pdf.table_header(cols, widths)
    zebra = 0
    for task_id, label, comp in all_tasks:
        for j, m in enumerate(models):
            pi_oh = agg_val(agg_idx, task_id, m, "pi",          "overhead")
            cc_oh = agg_val(agg_idx, task_id, m, "claude-code", "overhead")
            faktor = f"{cc_oh/pi_oh:.1f}x" if pi_oh else "—"
            pdf.table_row([
                label if j == 0 else "",
                comp  if j == 0 else "",
                m,
                f"{pi_oh:,.0f}",
                f"{cc_oh:,.0f}",
                faktor,
            ], widths, ["L","L","L","R","R","C"], zebra=(zebra % 2 == 0),
               bold_cols=[5], repeat_header=(cols, widths))
            zebra += 1
    pdf.ln(1)
    pdf.para("* medium-bash: im Docker-Container fair gemessen (beide Harnesses nativ Linux, ADR-0005).")

    # ------------------------------------------------------------------
    # 8. Ergebnisse: Kosten alle Tasks
    # ------------------------------------------------------------------
    pdf.section("8  Ergebnisse: Kosten — alle Tasks")
    pdf.para(
        "Median-Kosten (USD) je Task × Modell × Harness. "
        "Kosten einheitlich aus Tokens berechnet (pricing.py)."
    )

    cols = ["Task", "Kompl.", "Modell", "Pi ($)", "CC ($)", "Faktor"]
    widths = [38, 20, 25, 30, 30, 22]
    pdf.table_header(cols, widths)
    zebra = 0
    for task_id, label, comp in all_tasks:
        for j, m in enumerate(models):
            pi_c  = agg_val(agg_idx, task_id, m, "pi",          "cost_usd")
            cc_c  = agg_val(agg_idx, task_id, m, "claude-code", "cost_usd")
            faktor = f"{cc_c/pi_c:.1f}x" if pi_c else "—"
            pdf.table_row([
                label if j == 0 else "",
                comp  if j == 0 else "",
                m,
                f"${pi_c:.5f}",
                f"${cc_c:.5f}",
                faktor,
            ], widths, ["L","L","L","R","R","C"], zebra=(zebra % 2 == 0),
               bold_cols=[5], repeat_header=(cols, widths))
            zebra += 1
    pdf.ln(1)
    pdf.para(
        "Der Kosten-Faktor liegt typisch bei 4–6× für einfache Tasks, "
        "kann aber je nach Token-Zusammensetzung (Output-Anteil) variieren."
    )

    # ------------------------------------------------------------------
    # 9. Qualitätsbewertung
    # ------------------------------------------------------------------
    pdf.section("9  Qualitätsbewertung (Blindtest)")
    quality = d.get("quality", {})
    summary = quality.get("summary", {})

    pdf.section("Methodik Blindtest", level=2)
    pdf.bullet([
        f"Richter: {quality.get('judge_default', 'Opus 4.8')} "
        f"(Fallback {quality.get('judge_fallback', 'Sonnet 4.6')} bei Opus-Aufgaben)",
        "Methode: blind, A/B randomisiert, Swap-Test (2 Durchläufe je Paar)",
        f"Kriterien: {', '.join(quality.get('criteria', []))} (je 1–5 Punkte)",
        f"Paare bewertet: {summary.get('n_pairs', 27)}",
        f"Fehler: {summary.get('n_errors', 0)}",
        f"Position-Bias-Fälle (ausgewertet): {summary.get('position_bias_count', 3)}",
    ])

    pdf.section("Gesamtergebnis", level=2)
    wins = summary.get("wins", {})
    pi_score = summary.get("pi_mean_score", 0)
    cc_score = summary.get("cc_mean_score", 0)
    cols = ["", "Pi", "Claude Code", "Unentschieden"]
    widths = [60, 40, 40, 40]
    pdf.table_header(cols, widths)
    pdf.table_row(["Siege", str(wins.get("pi", 0)), str(wins.get("cc", 0)), str(wins.get("tie", 0))],
                  widths, ["L","C","C","C"])
    pdf.table_row(["Ø-Score (1–5)", f"{pi_score:.2f}", f"{cc_score:.2f}",
                   f"Delta: {cc_score - pi_score:.2f}"],
                  widths, ["L","C","C","C"], zebra=True)
    pdf.ln(1)
    pdf.para(
        "Fazit: Kein bedeutsamer Qualitätsunterschied. Beide Harnesses liefern hohe Qualität "
        "(Ø > 4,3/5). CC liegt minimal vorn (+0,41 Punkte), aber auf gleichem Modell "
        "und gleichen Prompts. Qualitätsdifferenz ist deutlich kleiner als Overhead-Differenz."
    )

    pdf.section("Einzelergebnisse je Task × Modell", level=2)
    judgements = quality.get("judgements", [])
    cols = ["Task", "Modell", "Erg.", "Pi", "CC", "Begründung"]
    widths = [38, 25, 15, 12, 12, 78]  # gesamt = 180mm
    pdf.table_header(cols, widths)
    for i, j in enumerate(judgements):
        winner_label = {"pi": "Pi", "cc": "CC", "tie": "Tie"}.get(j.get("winner","tie"), "?")
        justif = j.get("justification", "")  # kein Limit — table_row_wrap bricht um
        pdf.table_row_wrap([
            j.get("task_id",""),
            j.get("model_label",""),
            winner_label,
            f"{j.get('pi_overall', 0):.1f}",
            f"{j.get('cc_overall', 0):.1f}",
            justif,
        ], widths, ["L","L","C","C","C","L"], zebra=(i % 2 == 0),
           bold_cols=[2], repeat_header=(cols, widths))
    pdf.ln(1)

    # ------------------------------------------------------------------
    # 10. ADR-Zusammenfassungen
    # ------------------------------------------------------------------
    pdf.section("10  Architecture Decision Records (ADRs)")
    pdf.para("Alle harten Entscheidungen und Befunde mit Datum.")

    adrs = [
        ("ADR-0001", "2026-06-25", "Pi-Caching ist modellabhängig",
         "Pi nutzt je nach Modell unterschiedliches Caching: Haiku 4.5 gar kein Caching (input only), "
         "Sonnet 4.6 + Opus 4.8 aktivieren server-seitiges Prompt-Caching ab run#0. "
         "Token-Overhead ist kalt/warm-stabil; Kosten variieren (~2,3× kalt/warm)."),
        ("ADR-0002", "2026-06-25", "Pi turn_end-Summierung bei Tool-Runs",
         "Pi meldet Tokens pro Turn, nicht kumulativ. Alle turn_end-Events müssen summiert werden. "
         "Das input-Feld ist bei Tool-Runs ~1–3 Tokens (Pi packt den User-Prompt in cacheWrite). "
         "total_tokens ist die verlässliche Vergleichsgröße."),
        ("ADR-0003", "2026-06-29", "medium-bash war environment-asymmetrisch — Aufgabe ersetzt",
         "Ursprünglicher Prompt fragte nach /usr/share/doc (Linux-Pfad). "
         "CC lief als Windows-Prozess und fand diesen Pfad nicht zuverlässig. "
         "Ersetzt durch environment-agnostischen Systeminfo-Task (OS, CPU, RAM, Docker-Version)."),
        ("ADR-0004", "2026-06-30", "Plattform-Asymmetrie CC=Windows, Pi=Linux",
         "claude ist in der WSL-Umgebung ein Windows-Binary (/mnt/c/.../npm/claude), "
         "pi läuft nativ unter Linux/WSL. Betrifft alle Tool-/Multi-Turn-Tasks (verfälschte Tokens, "
         "Turns, Laufzeit). Die Single-Turn-Overhead-Kernzahl (~8×) ist OS-unabhängig und bleibt gültig. "
         "Lösung: Docker-Container (beide Harnesses nativ Linux)."),
        ("ADR-0005", "2026-06-30", "Datenquellen-Merge — faire Gesamtsuite",
         "benchmark-d1b7ef63.json (540 Runs, CC=Windows) wurde mit dem fairen medium-bash-Lauf aus "
         "dem Container (benchmark-c066a92f.json, CC+Pi=Linux) zur Gesamtsuite benchmark-9a72151a.json "
         "zusammengeführt. Gemischte Provenienz ist im JSON dokumentiert. "
         "Tool-Faktor medium-bash: 4,7–6,8× (statt 14–22× Messartefakt)."),
    ]
    for adr_id, datum, titel, text in adrs:
        pdf.check_pb(35)
        pdf.set_font("Sans", "B", 10)
        pdf.set_text_rgb(C_ANTHRAZIT)
        pdf.cell(0, 6, f"{adr_id} ({datum}): {titel}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Sans", "", 9)
        pdf.set_text_rgb(C_DARK)
        pdf.set_x(15)
        pdf.multi_cell(180, 5, text)
        pdf.ln(1)

    # ------------------------------------------------------------------
    # 11. Einschränkungen & offene Fragen
    # ------------------------------------------------------------------
    pdf.section("11  Einschränkungen & offene Fragen")
    pdf.bullet([
        "Cache-TTL für Claude-4-Modelle nicht explizit verifiziert. "
        "Annahme: 5 Minuten (analog claude-3). Nicht aus Messdaten direkt ableitbar.",
        "Stabiler CC-Kern (cache_read ~21.500 Tokens bereits bei run#0) ist Beobachtung, "
        "kein belegter Fakt. Mögliche Erklärung: Anthropic-seitiges Langzeit-Caching für CC.",
        "Pi-Caching-Ursache bei Sonnet/Opus unklar (minimale Schwellwert-Differenz, "
        "oder modellspezifische Anthropic-Konfiguration).",
        "Qualitätsbewertung: nur 27 Paare (baseline/trivial/simple/medium/complex, kein Real-Task). "
        "Statistisch begrenzt. Richter = Opus → Opus-Ergebnisse mit Sonnet bewertet.",
        "Modellpreise Stand Juni 2026. Bei Änderungen pricing.py aktualisieren.",
    ])

    # ------------------------------------------------------------------
    # 12. Provenienz
    # ------------------------------------------------------------------
    pdf.section("12  Provenienz")
    prov = d.get("provenance", {})
    pdf.para(f"Suite-ID: {VERSION}")
    pdf.para(f"Plattform: {prov.get('platform', 'n/a')}")
    pdf.para(f"Python: {prov.get('python', 'n/a')}")
    tv = prov.get("tool_versions", {})
    pdf.para(f"Tool-Versionen: Pi {tv.get('pi','?')}  |  Claude Code {tv.get('claude','?')}")
    pdf.para(f"Wiederholungen: {prov.get('repeat', 10)}")
    pdf.para(f"Sandbox: {prov.get('sandbox', 'n/a')}")

    mp = prov.get("merge_provenance", {})
    if mp:
        pdf.section("Merge-Provenienz (ADR-0005)", level=2)
        pdf.para(f"Basis-Suite: {mp.get('base_suite', '?')} — Plattform: {mp.get('base_platform','?')[:60]}")
        pdf.para(f"Override-Suite: {mp.get('override_suite','?')} (Task: {mp.get('overridden_task','?')})")
        pdf.para(f"Warnung: {mp.get('warning','')}")

    # Ausgabe
    out = OUT_DIR / "token-benchmark-methodik-ergebnisse.pdf"
    pdf.output(str(out))
    print(f"PDF 1 -> {out}")


# ---------------------------------------------------------------------------
# PDF 2: Nutzung & Ausblick
# ---------------------------------------------------------------------------
def build_pdf2():
    pdf = DocPDF("Token-Benchmark: Nutzung & Anleitung")
    pdf.title_page(
        "Anleitung für Kollegen — Tool starten, Container, Grenzen",
        "Internes Dokument · SelectLine Software AG"
    )

    # ------------------------------------------------------------------
    # 1. Schnellstart UI
    # ------------------------------------------------------------------
    pdf.add_page()
    pdf.section("1  Schnellstart — Web-UI")
    pdf.para(
        "Die Web-UI ist die empfohlene Bedienoberfläche. "
        "Sie läuft lokal im Browser und braucht keine Installation außer Python 3.10+."
    )
    url = "https://github.com/Schnoitzel/token-benchmark"
    pdf.set_font("Sans", "", 10)
    pdf.set_text_rgb((0x00, 0x56, 0xB3))  # Blau wie ein Hyperlink
    pdf.set_x(15)
    pdf.cell(0, 5.5, f"Repository: {url}", link=url, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_rgb(C_DARK)
    pdf.ln(1)
    pdf.para("Voraussetzung: Pi und Claude Code müssen auf dem Host eingeloggt sein "
             "(OAuth, s. Abschnitt 5).")
    pdf.code_block("""# Im Repository-Verzeichnis:
python3 server.py

# Dann im Browser (Windows) öffnen:
http://localhost:8000""")

    pdf.section("Was die UI kann", level=2)
    pdf.bullet([
        "Task + Modell + Anzahl Wiederholungen auswählen und Benchmark starten",
        "Ergebnisse live verfolgen (Token-Breakdown: input / cache↑write / cache↓read / output / Overhead / Total)",
        "Tabellen mit Median + min–max je Kombination (aus aggregates)",
        "Drill-down: Kosten-Breakdown, Methodik-Erklärung ('Wie erhoben?'), Provenienz",
        "Theme-Umschalter (dunkel/hell), Präsentations-Modus (3 Kernzahlen)",
        "Qualität bewerten (Button 'Qualität bewerten' → /api/judge, blinder LLM-Richter)",
        "Real-Task-Reset (Button 'Repo zurücksetzen' → git restore .)",
        "Letzte Suite laden und alle bisherigen Ergebnisse anzeigen",
    ])

    # ------------------------------------------------------------------
    # 2. CLI-Nutzung
    # ------------------------------------------------------------------
    pdf.section("2  CLI-Nutzung")
    pdf.para("Alternative zur UI für schnelle, scriptbare Läufe.")

    pdf.section("Häufige Befehle", level=2)
    cmds = [
        ("Trockenlauf (keine echten Kosten)",
         "python3 main.py --dry-run"),
        ("Overhead-Kernzahl messen (5 Wdh.)",
         "python3 main.py --complexity baseline --repeat 5"),
        ("Alle Tasks, Haiku, 3 Wdh.",
         "python3 main.py --models 'Haiku 4.5' --repeat 3"),
        ("Einzelner Task, alle Modelle",
         "python3 main.py --tasks medium-bash --repeat 10"),
        ("Bericht aus neuestem Lauf",
         "python3 report.py"),
        ("Blinde Qualitätsbewertung (Opus-Richter)",
         "python3 judge.py"),
    ]
    for desc, cmd in cmds:
        pdf.check_pb(14)
        pdf.set_font("Sans", "B", 9)
        pdf.set_text_rgb(C_ANTHRAZIT)
        pdf.cell(0, 5, desc, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.code_block(cmd)

    pdf.section("Alle Parameter (main.py --help)", level=2)
    cols = ["Parameter", "Bedeutung", "Default"]
    widths = [45, 95, 40]
    pdf.table_header(cols, widths)
    params = [
        ("--complexity",   "Nur Tasks dieser Komplexität (baseline/trivial/simple/medium/complex/real/all)", "all"),
        ("--tasks",        "Kommagetrennte Task-IDs (z.B. baseline-overhead,trivial-fact)",                  "alle"),
        ("--models",       "Kommagetrennte Modell-Labels (z.B. 'Haiku 4.5')",                               "alle"),
        ("--harnesses",    "Nur dieser Harness (pi / claude-code)",                                         "beide"),
        ("--repeat",       "Wiederholungen je Kombination",                                                  "1"),
        ("--output",       "Pfad zur Ausgabe-JSON (default: results/benchmark-<id>.json)",                  "auto"),
        ("--dry-run",      "Keine echten API-Aufrufe, Dummy-Antworten",                                     "—"),
    ]
    for i, r in enumerate(params):
        pdf.table_row_wrap(r, widths, ["L","L","C"], zebra=(i % 2 == 0),
                           bold_cols=[0], repeat_header=(cols, widths))
    pdf.ln(1)

    # ------------------------------------------------------------------
    # 3. Modelle & Tasks anpassen
    # ------------------------------------------------------------------
    pdf.section("3  Modelle & Tasks anpassen")

    pdf.section("Modelle (models.py)", level=2)
    pdf.para(
        "Modelle sind in models.py als Liste von Model-Objekten definiert. "
        "Jedes Modell hat label, pi_id (Pi-Flag --model) und cc_id (Claude Code --model). "
        "Zum Hinzufügen einfach neues Model(...)-Objekt in MODELS einhängen."
    )
    pdf.code_block("""# Beispiel: neues Modell hinzufügen (models.py)
from models import Model, MODELS
# MODELS.append(Model("Haiku 3.5", "claude-haiku-3-5", "haiku-3-5"))""")

    pdf.section("Tasks (tasks.py)", level=2)
    pdf.para(
        "Tasks sind in tasks.py als Liste von Task-Objekten definiert. "
        "Pflichtfelder: id, complexity, prompt. Optional: use_tools=True, num_turns, repo_dir."
    )
    pdf.code_block("""# Beispiel: neuen Task hinzufügen (tasks.py)
from tasks import Task, TASKS
# TASKS.append(Task(
#     id="mein-task",
#     complexity="simple",
#     prompt="Erkläre X in drei Sätzen.",
# ))""")
    pdf.para(
        "Wichtig: Synthetische Tasks dürfen keine Pfad-Abhängigkeiten enthalten "
        "(laufen in leerer Sandbox). Real-Tasks brauchen repo_dir."
    )

    pdf.section("Preise (pricing.py)", level=2)
    pdf.para(
        "Alle Kosten werden einheitlich aus pricing.py berechnet. "
        "Bei Preisänderungen nur diese eine Datei aktualisieren."
    )

    # ------------------------------------------------------------------
    # 4. Container-Setup
    # ------------------------------------------------------------------
    pdf.section("4  Container-Setup (Docker)")
    pdf.para(
        "Der Container ermöglicht faire Messungen (beide Harnesses nativ Linux) "
        "und einfache Distribution an Kollegen."
    )
    pdf.para("Voraussetzungen: Docker installiert, eigener Anthropic-OAuth-Zugang.")

    pdf.section("Schnellstart", level=2)
    pdf.code_block("""# 1. Image bauen (einmalig, ~400 MB)
docker build -t token-benchmark .

# 2. Host-Credentials importieren (Pi + CC müssen auf dem Host eingeloggt sein)
./docker/run.sh import-creds

# 3. UI starten (http://localhost:8000)
./docker/run.sh ui

# 4. Oder: CLI-Benchmark
./docker/run.sh bench --tasks medium-bash --repeat 10""")

    pdf.section("Alle run.sh-Befehle", level=2)
    cols = ["Befehl", "Was es tut"]
    widths = [62, 118]
    pdf.table_header(cols, widths)
    run_cmds = [
        ("./docker/run.sh ui",               "Startet Web-UI auf Port 8000"),
        ("./docker/run.sh bench [args]",     "Startet main.py mit beliebigen Parametern"),
        ("./docker/run.sh import-creds",     "Importiert Pi + CC Credentials vom Host"),
        ("./docker/run.sh login",            "Interaktiver Login im Container (headless)"),
        ("./docker/run.sh shell",            "Bash im Container (für Debugging)"),
    ]
    for i, r in enumerate(run_cmds):
        pdf.table_row_wrap(r, widths, ["L","L"], zebra=(i % 2 == 0),
                           bold_cols=[0], repeat_header=(cols, widths))
    pdf.ln(1)

    pdf.section("Hinweise zum Login", level=2)
    pdf.bullet([
        "Empfohlen: Host-Credentials importieren (./docker/run.sh import-creds). "
        "Voraussetzung: Pi (TUI: /login) und Claude Code (claude auth login) "
        "müssen vorher auf dem Host eingeloggt sein.",
        "Credentials werden in ein persistentes Docker-Volume (~/.pi, ~/.config/claude) gemountet "
        "und bleiben nach Container-Neustart erhalten.",
        "Jeder Kollege loggt sich selbst ein — kein Key-Weitergabe nötig.",
        "Real-Tasks werden im Container automatisch übersprungen (repo_dir nicht verfügbar).",
    ])

    pdf.section("Ergebnisse persistieren", level=2)
    pdf.para(
        "Das results/-Verzeichnis wird vom Host gemountet (./results:/app/results). "
        "Ergebnisse landen direkt auf dem Host und bleiben nach Container-Stopp erhalten."
    )

    # ------------------------------------------------------------------
    # 5. Bekannte Grenzen
    # ------------------------------------------------------------------
    pdf.section("5  Bekannte Grenzen & Hinweise")

    cols = ["Aspekt", "Einschränkung"]
    widths = [50, 130]
    pdf.table_header(cols, widths)
    limits = [
        ("Real-Tasks",
         "Werden im Container übersprungen (JavaFX-Repo nicht im Container). "
         "Nur auf dem Host mit repo_dir konfigurierbar."),
        ("Plattform-Asymmetrie (Host)",
         "Auf dem Windows/WSL-Host laufen Pi (Linux) und CC (Windows-Binary) in "
         "verschiedenen OS. Betrifft Tool-Tasks, NICHT den Single-Turn-Overhead (~8×)."),
        ("OAuth-Login",
         "Das Tool nutzt ausschließlich OAuth (kein API-Key). Jeder Nutzer braucht "
         "ein aktives Anthropic-Abo (Claude Pro / Team)."),
        ("Cache-TTL",
         "5-Minuten-TTL für Prompt-Cache angenommen (claude-3-Doku). "
         "Für Claude-4-Modelle nicht explizit verifiziert."),
        ("Qualitätsbewertung",
         "judge.py verbraucht Opus 4.8 Tokens (teuer). Nur bei Bedarf ausführen. "
         "Bei Opus-Aufgaben wird Sonnet 4.6 als Richter verwendet."),
        ("Preise",
         "Stand Juni 2026. Bei Änderungen pricing.py aktualisieren."),
    ]
    for i, r in enumerate(limits):
        pdf.table_row_wrap(r, widths, ["L","L"], zebra=(i % 2 == 0),
                           bold_cols=[0], repeat_header=(cols, widths))
    pdf.ln(1)

    # Ausgabe
    out = OUT_DIR / "token-benchmark-nutzung-anleitung.pdf"
    pdf.output(str(out))
    print(f"PDF 2 -> {out}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    only1 = "--pdf1" in sys.argv
    only2 = "--pdf2" in sys.argv

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not only2:
        print("Lade Daten...")
        d, agg_idx = load_data()
        print(f"  {len(d['results'])} Ergebnisse, {len(d.get('aggregates',[]))} Aggregate")
        print("Erzeuge PDF 1 (Methodik & Ergebnisse)...")
        build_pdf1(d, agg_idx)

    if not only1:
        print("Erzeuge PDF 2 (Nutzung & Ausblick)...")
        build_pdf2()

    print("Fertig.")


if __name__ == "__main__":
    main()
