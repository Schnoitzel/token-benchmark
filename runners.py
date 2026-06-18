"""
Runner: starten Pi bzw. Claude Code als Unterprozess und lesen die
Token-Daten aus deren JSON-Ausgabe.

WICHTIG (Pi): Im Print-Modus (-p) liest Pi auch stdin und wartet auf EOF.
Wird Pi mit offener stdin-Pipe gestartet, wartet es ewig. Deshalb leiten wir
stdin von /dev/null um (stdin=DEVNULL) -> Pi laeuft sofort durch.
"""

import json
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from models import Model
from tasks import Task


# --- Exakte Flags, die wir verwenden (auch fuer den Provenienz-Block) -------
# Pi laeuft bewusst "blank": keine Kontext-Dateien, keine Prompt-Templates,
# kein Thinking, ephemere Session, in leerem Arbeitsverzeichnis.
PI_FLAGS = "-p --mode json --no-session --no-context-files --no-prompt-templates --thinking off --model <id>"
# Claude Code: nicht-interaktiv, JSON, keine Berechtigungsabfragen.
CC_FLAGS = "-p --output-format json --model <id> --allow-dangerously-skip-permissions"


@dataclass
class TokenUsage:
    input_tokens: int = 0       # Nicht-gecachte Input-Tokens (inkl. System-Prompt wenn kein Caching)
    output_tokens: int = 0      # vom Modell generiert
    cache_read: int = 0         # gecachte Tokens aus vorherigem Aufruf
    cache_write: int = 0        # System-Prompt beim ersten Aufruf
    total_tokens: int = 0       # Summe aller obigen
    cost_usd: float = 0.0       # Gesamtkosten in USD (einheitlich berechnet, siehe pricing.py)
    cost_harness_usd: float = 0.0  # vom Harness selbst gemeldete Kosten (nur zur Transparenz)


@dataclass
class RunResult:
    harness: str                # "pi" | "claude-code"
    model_label: str
    task_id: str
    task_complexity: str
    task_prompt: str
    duration_ms: int
    usage: TokenUsage
    response: str
    timestamp: str
    repeat_index: int = 0       # 0-basierter Index der Wiederholung (fuer Statistik)
    error: str | None = None
    raw: dict = field(default_factory=dict)


def _run_process(cmd: list[str], timeout_s: int, cwd: str | None = None) -> tuple[str, str, bool]:
    """Startet einen Prozess mit geschlossenem stdin. Gibt (stdout, stderr, timed_out).

    cwd: Arbeitsverzeichnis. Wir starten beide Harnesses bewusst in einem
    LEEREN temporaeren Ordner, damit keine AGENTS.md / CLAUDE.md aus dem
    Projektordner als "Gedaechtnis" mitgeladen wird (fairer Blank-Vergleich).
    """
    try:
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,   # <- kritisch fuer Pi
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_s,
            text=True,
            cwd=cwd,
        )
        return proc.stdout, proc.stderr, False
    except subprocess.TimeoutExpired as e:
        out = e.stdout or ""
        err = e.stderr or ""
        if isinstance(out, bytes):
            out = out.decode(errors="replace")
        if isinstance(err, bytes):
            err = err.decode(errors="replace")
        return out, err, True


# --- Pi ---------------------------------------------------------------------

def run_pi(task: Task, model: Model) -> RunResult:
    start = time.time()
    timestamp = datetime.now(timezone.utc).isoformat()

    cmd = [
        "pi",
        "-p", task.prompt,
        "--mode", "json",
        "--no-session",
        "--no-context-files",     # entfernt AGENTS.md/CLAUDE.md Overhead auf Pi-Seite
        "--no-prompt-templates",  # keine Prompt-Template-Discovery (blank)
        "--thinking", "off",      # kein extended thinking, fairer Token-Vergleich
        "--model", model.pi_model,
    ]

    # Leeres Sandbox-Verzeichnis -> kein Zugriff auf projekteigene AGENTS.md/CLAUDE.md
    with tempfile.TemporaryDirectory(prefix="benchmark-pi-") as sandbox:
        stdout, stderr, timed_out = _run_process(cmd, timeout_s=120, cwd=sandbox)
    duration_ms = int((time.time() - start) * 1000)

    error = "Pi-Run nach 120s abgebrochen (Timeout)" if timed_out else None

    # JSONL-Zeilen parsen
    events = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    usage = TokenUsage()
    response = ""

    # letztes turn_end-Event suchen
    turn_end = next((e for e in reversed(events) if e.get("type") == "turn_end"), None)
    if turn_end:
        msg = turn_end["message"]
        u = msg["usage"]
        usage = TokenUsage(
            input_tokens=u["input"],
            output_tokens=u["output"],
            cache_read=u["cacheRead"],
            cache_write=u["cacheWrite"],
            total_tokens=u["totalTokens"],
            cost_usd=u["cost"]["total"],
        )
        response = "\n".join(
            c.get("text", "") for c in msg["content"] if c.get("type") == "text"
        ).strip()

    if not error and not response and not turn_end:
        error = "Keine turn_end-Daten in Pi-Ausgabe gefunden"

    return RunResult(
        harness="pi",
        model_label=model.label,
        task_id=task.id,
        task_complexity=task.complexity,
        task_prompt=task.prompt,
        duration_ms=duration_ms,
        usage=usage,
        response=response,
        timestamp=timestamp,
        error=error,
        raw={"events": len(events), "stderr": stderr[:500]},
    )


# --- Claude Code ------------------------------------------------------------

def run_claude(task: Task, model: Model) -> RunResult:
    start = time.time()
    timestamp = datetime.now(timezone.utc).isoformat()

    cmd = [
        "claude",
        "-p", task.prompt,
        "--output-format", "json",
        "--model", model.cc_model,
        "--allow-dangerously-skip-permissions",  # keine interaktiven Nachfragen
    ]

    # Leeres Sandbox-Verzeichnis -> Claude entdeckt keine AGENTS.md/CLAUDE.md (Blank-Lauf)
    with tempfile.TemporaryDirectory(prefix="benchmark-cc-") as sandbox:
        stdout, stderr, timed_out = _run_process(cmd, timeout_s=180, cwd=sandbox)
    duration_ms = int((time.time() - start) * 1000)

    error = "Claude-Run nach 180s abgebrochen (Timeout)" if timed_out else None

    usage = TokenUsage()
    response = ""
    raw: dict = {}

    if not error:
        try:
            parsed = json.loads(stdout.strip())
            raw = parsed
            u = parsed["usage"]
            inp = u["input_tokens"]
            out = u["output_tokens"]
            c_read = u["cache_read_input_tokens"]
            c_write = u["cache_creation_input_tokens"]
            usage = TokenUsage(
                input_tokens=inp,
                output_tokens=out,
                cache_read=c_read,
                cache_write=c_write,
                total_tokens=inp + out + c_read + c_write,
                cost_usd=parsed["total_cost_usd"],
            )
            response = parsed.get("result", "")
            if parsed.get("is_error") or parsed.get("subtype") != "success":
                error = f"Claude Code Fehler: {parsed.get('result')}"
        except (json.JSONDecodeError, KeyError) as e:
            error = f"JSON-Parsing fehlgeschlagen: {e}\nStdout: {stdout[:500]}"

    return RunResult(
        harness="claude-code",
        model_label=model.label,
        task_id=task.id,
        task_complexity=task.complexity,
        task_prompt=task.prompt,
        duration_ms=duration_ms,
        usage=usage,
        response=response,
        timestamp=timestamp,
        error=error,
        raw=raw if isinstance(raw, dict) else {},
    )


# --- Versions-/Provenienz-Infos --------------------------------------------

def get_tool_versions() -> dict[str, str]:
    """Liest `pi --version` und `claude --version` fuer den Provenienz-Block."""
    def _ver(cmd: list[str]) -> str:
        try:
            out = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=20,
            )
            lines = [l.strip() for l in (out.stdout or "").splitlines() if l.strip()]
            return lines[0] if lines else "?"
        except Exception as e:  # noqa: BLE001
            return f"unbekannt ({e})"

    return {"pi": _ver(["pi", "--version"]), "claude": _ver(["claude", "--version"])}
