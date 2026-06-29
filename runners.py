"""
Runner: starten Pi bzw. Claude Code als Unterprozess und lesen die
Token-Daten aus deren JSON-Ausgabe.

WICHTIG (Pi): Im Print-Modus (-p) liest Pi auch stdin und wartet auf EOF.
Wird Pi mit offener stdin-Pipe gestartet, wartet es ewig. Deshalb leiten wir
stdin von /dev/null um (stdin=DEVNULL) -> Pi laeuft sofort durch.

Fuer echte Projektaufgaben (task.repo_dir gesetzt):
  - Harness laeuft direkt im Repo-Verzeichnis (kein leeres Sandbox-Verzeichnis).
  - Nach dem Run wird `git diff` erfasst und an die Antwort angehaengt.
  - KEIN Auto-Reset: Dateiaenderungen bleiben bestehen, damit der Nutzer
    die App bauen und die UI-Aenderungen pruefen kann. Reset erfolgt manuell
    ueber den UI-Button oder `git restore .`.
"""

import json
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from models import Model
from tasks import Task


# --- Exakte Flags, die wir verwenden (auch fuer den Provenienz-Block) -------
PI_FLAGS = "-p --mode json --no-session --no-context-files --no-prompt-templates --thinking off --model <id>"
CC_FLAGS = "-p --output-format json --model <id> --allow-dangerously-skip-permissions"

# Timeouts in Sekunden
TIMEOUT_SANDBOX = 120    # leere Sandbox (keine Tools)
TIMEOUT_SANDBOX_TOOLS = 180  # leere Sandbox mit Tools
TIMEOUT_REPO = 600       # echtes Repo (viele Dateien, Opus kann lange brauchen)


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    cache_write: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    cost_harness_usd: float = 0.0


@dataclass
class RunResult:
    harness: str
    model_label: str
    task_id: str
    task_complexity: str
    task_prompt: str
    duration_ms: int
    usage: TokenUsage
    response: str
    timestamp: str
    repeat_index: int = 0
    error: str | None = None
    raw: dict = field(default_factory=dict)


def _run_process(cmd: list[str], timeout_s: int, cwd: str | None = None) -> tuple[str, str, bool]:
    """Startet einen Prozess mit geschlossenem stdin. Gibt (stdout, stderr, timed_out)."""
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


def _git_diff(repo_dir: str) -> str:
    """Gibt `git diff` des Repos zurueck (nur geaenderte Dateien, kein Diff von
    neu erstellten/ungetracken Dateien). Leer wenn nichts geaendert wurde."""
    try:
        result = subprocess.run(
            ["git", "diff"],
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=15,
        )
        return result.stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


# --- Pi ---------------------------------------------------------------------

def run_pi(task: Task, model: Model) -> RunResult:
    start = time.time()
    timestamp = datetime.now(timezone.utc).isoformat()

    cmd = [
        "pi",
        "-p", task.prompt,
        "--mode", "json",
        "--no-session",
        "--no-context-files",
        "--no-prompt-templates",
        "--thinking", "off",
        "--model", model.pi_model,
    ]

    if task.repo_dir:
        # Echtes Repo: pruefen ob vorhanden, dann direkt darin laufen
        if not os.path.isdir(task.repo_dir):
            return RunResult(
                harness="pi", model_label=model.label, task_id=task.id,
                task_complexity=task.complexity, task_prompt=task.prompt,
                duration_ms=0, usage=TokenUsage(), response="",
                timestamp=timestamp,
                error=f"repo_dir nicht gefunden: {task.repo_dir}",
            )
        stdout, stderr, timed_out = _run_process(cmd, timeout_s=TIMEOUT_REPO, cwd=task.repo_dir)
        diff = _git_diff(task.repo_dir)
        duration_ms = int((time.time() - start) * 1000)
        error = f"Pi-Run nach {TIMEOUT_REPO}s abgebrochen (Timeout)" if timed_out else None
    else:
        # Leeres Sandbox-Verzeichnis (Standard fuer alle anderen Tasks)
        timeout = TIMEOUT_SANDBOX_TOOLS if task.use_tools else TIMEOUT_SANDBOX
        with tempfile.TemporaryDirectory(prefix="benchmark-pi-") as sandbox:
            stdout, stderr, timed_out = _run_process(cmd, timeout_s=timeout, cwd=sandbox)
        diff = ""
        duration_ms = int((time.time() - start) * 1000)
        error = f"Pi-Run nach {timeout}s abgebrochen (Timeout)" if timed_out else None

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

    # Pi meldet Token-Nutzung PRO TURN (nicht kumulativ).
    # Bei Tool-Runs gibt es viele turn_end-Events -> alle summieren.
    turn_ends = [e for e in events if e.get("type") == "turn_end"]
    if turn_ends:
        inp = sum(e["message"]["usage"]["input"] for e in turn_ends)
        out = sum(e["message"]["usage"]["output"] for e in turn_ends)
        c_read = sum(e["message"]["usage"]["cacheRead"] for e in turn_ends)
        c_write = sum(e["message"]["usage"]["cacheWrite"] for e in turn_ends)
        cost = sum(e["message"]["usage"]["cost"]["total"] for e in turn_ends)
        usage = TokenUsage(
            input_tokens=inp,
            output_tokens=out,
            cache_read=c_read,
            cache_write=c_write,
            total_tokens=inp + out + c_read + c_write,
            cost_usd=cost,
        )
        # Antworttext aus dem letzten turn_end
        last_msg = turn_ends[-1]["message"]
        response = "\n".join(
            c.get("text", "") for c in last_msg["content"] if c.get("type") == "text"
        ).strip()
        if diff:
            response = (response + "\n\n---\n**git diff:**\n```diff\n" + diff + "\n```").strip()

    if not error and not response and not turn_ends:
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
        raw={"events": len(events), "num_turns": len(turn_ends), "stderr": stderr[:500]},
    )


# --- Claude Code ------------------------------------------------------------

def run_claude(task: Task, model: Model) -> RunResult:
    start = time.time()
    timestamp = datetime.now(timezone.utc).isoformat()

    # --settings: explizite Allow-Liste fuer File-Edits.
    # --allow-dangerously-skip-permissions allein reicht bei CC >= 2.1.x nicht mehr
    # fuer Schreibzugriffe auf Dateien ausserhalb des cwd (Windows-Pfad-Problem in WSL).
    _ALLOW_SETTINGS = '{"permissions":{"allow":["Edit(*)","MultiEdit(*)","Write(*)","Bash(*)"]}}'

    cmd = [
        "claude",
        "-p", task.prompt,
        "--output-format", "json",
        "--model", model.cc_model,
        "--allow-dangerously-skip-permissions",
        "--settings", _ALLOW_SETTINGS,
    ]

    if task.repo_dir:
        # Repo-Verzeichnis als trusted hinzufuegen (WSL-Pfad + Windows-Pfad).
        cmd.extend(["--add-dir", task.repo_dir])
        try:
            import subprocess as _sp
            win_path = _sp.check_output(
                ["wslpath", "-m", task.repo_dir], text=True  # -m: forward slashes (C:/...)
            ).strip()
            if win_path:
                cmd.extend(["--add-dir", win_path])
        except Exception:
            pass  # wslpath nicht verfuegbar (kein WSL) -> ignorieren

        # Echtes Repo: pruefen ob vorhanden, dann direkt darin laufen
        if not os.path.isdir(task.repo_dir):
            return RunResult(
                harness="claude-code", model_label=model.label, task_id=task.id,
                task_complexity=task.complexity, task_prompt=task.prompt,
                duration_ms=0, usage=TokenUsage(), response="",
                timestamp=timestamp,
                error=f"repo_dir nicht gefunden: {task.repo_dir}",
            )
        stdout, stderr, timed_out = _run_process(cmd, timeout_s=TIMEOUT_REPO, cwd=task.repo_dir)
        diff = _git_diff(task.repo_dir)
        duration_ms = int((time.time() - start) * 1000)
        error = f"Claude-Run nach {TIMEOUT_REPO}s abgebrochen (Timeout)" if timed_out else None
    else:
        # Leeres Sandbox-Verzeichnis (Standard)
        timeout = TIMEOUT_SANDBOX_TOOLS if task.use_tools else TIMEOUT_SANDBOX
        with tempfile.TemporaryDirectory(prefix="benchmark-cc-") as sandbox:
            stdout, stderr, timed_out = _run_process(cmd, timeout_s=timeout, cwd=sandbox)
        diff = ""
        duration_ms = int((time.time() - start) * 1000)
        error = f"Claude-Run nach {timeout}s abgebrochen (Timeout)" if timed_out else None

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
            if diff:
                response = (response + "\n\n---\n**git diff:**\n```diff\n" + diff + "\n```").strip()
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
