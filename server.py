#!/usr/bin/env python3
"""
server.py - kleiner lokaler Web-Server fuer die Benchmark-UI.

Start:
  python3 server.py            # oeffnet auf http://localhost:8000
  python3 server.py --port 9000

Dann im Browser http://localhost:8000 oeffnen.

Nutzt nur die Python-Standardbibliothek (keine Installation noetig).
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from core import filter_models, filter_tasks, run_benchmark_iter
from models import MODELS
from tasks import TASKS, Task

HERE = os.path.dirname(os.path.abspath(__file__))


class Handler(BaseHTTPRequestHandler):
    # Logmeldungen kurz halten
    def log_message(self, fmt, *args):  # noqa: A003
        pass

    # --- Hilfsfunktionen ---------------------------------------------------

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, content_type):
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # --- Routing -----------------------------------------------------------

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self._send_file(os.path.join(HERE, "static", "index.html"), "text/html; charset=utf-8")
            return

        if path == "/api/config":
            self._send_json({
                "models": [
                    {"label": m.label, "tier": m.tier} for m in MODELS
                ],
                "tasks": [
                    {"id": t.id, "complexity": t.complexity,
                     "description": t.description, "use_tools": t.use_tools}
                    for t in TASKS
                ],
            })
            return

        if path == "/api/results":
            files = sorted(glob.glob(os.path.join(HERE, "results", "benchmark-*.json")), reverse=True)
            items = []
            for fp in files:
                try:
                    with open(fp, encoding="utf-8") as f:
                        suite = json.load(f)
                    results = suite.get("results", [])

                    # Eindeutige Werte in stabiler Reihenfolge sammeln
                    def uniq(key):
                        seen = []
                        for r in results:
                            v = r.get(key)
                            if v and v not in seen:
                                seen.append(v)
                        return seen

                    harnesses = uniq("harness")
                    models = uniq("model_label")
                    task_ids = uniq("task_id")

                    # Bei eigenem Prompt einen Ausschnitt des Texts zeigen.
                    # Whitespace/Umbrüche zu einzelnen Leerzeichen normalisieren,
                    # damit mehrzeilige Prompts die Dropdown-Zeile nicht zerschießen.
                    custom_snippet = None
                    if task_ids == ["custom"]:
                        prompt = next((r.get("task_prompt", "") for r in results), "")
                        flat = " ".join(prompt.split())
                        limit = 80
                        if len(flat) > limit:
                            # Nicht mitten im Wort abschneiden: am letzten Leerzeichen vor dem Limit trennen
                            cut = flat[:limit]
                            last_space = cut.rfind(" ")
                            if last_space > 40:  # nur wenn dadurch nicht zu viel verloren geht
                                cut = cut[:last_space]
                            custom_snippet = cut.rstrip() + "…"
                        else:
                            custom_snippet = flat

                    items.append({
                        "run_id": suite["run_id"],
                        "started_at": suite.get("started_at"),
                        "num_results": len(results),
                        "harnesses": harnesses,
                        "models": models,
                        "task_ids": task_ids,
                        "custom_snippet": custom_snippet,
                    })
                except Exception:  # noqa: BLE001
                    pass
            self._send_json(items)
            return

        if path == "/api/result":
            run_id = qs.get("run_id", [""])[0]
            fp = os.path.join(HERE, "results", f"benchmark-{run_id}.json")
            if not os.path.exists(fp):
                self._send_json({"error": "not found"}, status=404)
                return
            with open(fp, encoding="utf-8") as f:
                self._send_json(json.load(f))
            return

        if path == "/api/run":
            self._handle_run_stream(qs)
            return

        if path == "/api/judge":
            self._handle_judge_stream(qs)
            return

        self._send_json({"error": "not found"}, status=404)

    # --- Benchmark-Lauf als SSE-Stream -------------------------------------

    def _handle_run_stream(self, qs):
        harnesses = qs.get("harnesses", ["pi,claude-code"])[0].split(",")
        harnesses = [h.strip() for h in harnesses if h.strip()]

        model_arg = qs.get("models", [""])[0]
        only_models = [m.strip() for m in model_arg.split(",") if m.strip()] or None

        task_arg = qs.get("tasks", [""])[0]
        only_tasks = [t.strip() for t in task_arg.split(",") if t.strip()] or None

        complexity_arg = qs.get("complexity", [""])[0]
        complexity = [c.strip() for c in complexity_arg.split(",") if c.strip()] or None

        # Eigener Prompt (optional): wird als Ad-hoc-Aufgabe getestet.
        custom_prompt = qs.get("custom_prompt", [""])[0].strip()
        custom_use_tools = qs.get("custom_use_tools", ["0"])[0] in ("1", "true", "on")

        try:
            delay = float(qs.get("delay", ["2"])[0])
        except ValueError:
            delay = 2.0

        try:
            repeat = max(1, int(qs.get("repeat", ["1"])[0]))
        except ValueError:
            repeat = 1

        models = filter_models(only_models)

        if custom_prompt:
            # Nur den eigenen Prompt testen – keine vordefinierten Aufgaben.
            tasks = [Task(
                id="custom",
                complexity="trivial",
                description="Eigener Prompt",
                prompt=custom_prompt,
                use_tools=custom_use_tools,
            )]
        else:
            tasks = filter_tasks(only_tasks, complexity)

        if not models or not tasks or not harnesses:
            self._send_json({"error": "Keine gueltige Auswahl"}, status=400)
            return

        # SSE-Header
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        def send_event(obj):
            data = "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"
            self.wfile.write(data.encode("utf-8"))
            self.wfile.flush()

        try:
            for event in run_benchmark_iter(harnesses, models, tasks, delay=delay, repeat=repeat):
                send_event(event)
        except (BrokenPipeError, ConnectionResetError):
            # Browser hat die Verbindung geschlossen - egal
            pass

    # --- Qualitaetsbewertung als SSE-Stream --------------------------------

    def _handle_judge_stream(self, qs):
        import judge as judge_mod

        run_id = qs.get("run_id", [""])[0]
        fp = os.path.join(HERE, "results", f"benchmark-{run_id}.json")
        if not run_id or not os.path.exists(fp):
            self._send_json({"error": "Lauf nicht gefunden"}, status=404)
            return

        with open(fp, encoding="utf-8") as f:
            suite = json.load(f)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        def send_event(obj):
            data = "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"
            self.wfile.write(data.encode("utf-8"))
            self.wfile.flush()

        try:
            quality = None
            for event in judge_mod.judge_suite_iter(suite):
                send_event(event)
                if event["type"] == "judge_done":
                    quality = event["quality"]
            # Ergebnis in die JSON zurueckschreiben
            if quality is not None:
                suite["quality"] = quality
                with open(fp, "w", encoding="utf-8") as f:
                    json.dump(suite, f, indent=2, ensure_ascii=False)
        except (BrokenPipeError, ConnectionResetError):
            pass


def _is_wsl() -> bool:
    try:
        with open("/proc/version", encoding="utf-8") as f:
            return "microsoft" in f.read().lower()
    except Exception:  # noqa: BLE001
        return False


def _open_browser(url: str) -> None:
    """Versucht den Browser zu oeffnen. Auf WSL ueber Windows. Fehler werden
    still geschluckt und ein Hinweis ausgegeben, falls es nicht klappt."""
    # WSL: Windows-Standardbrowser ueber explorer.exe/powershell oeffnen
    if _is_wsl():
        for cmd in (
            ["explorer.exe", url],
            ["powershell.exe", "-NoProfile", "Start-Process", url],
            ["wslview", url],
        ):
            exe = shutil.which(cmd[0])
            if not exe:
                continue
            try:
                subprocess.Popen(
                    cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                return
            except Exception:  # noqa: BLE001
                continue
        print("  (Browser bitte manuell oeffnen – siehe Adresse oben.)")
        return

    # Normales Linux/Mac/Windows: webbrowser, aber stderr unterdruecken
    try:
        import io
        import contextlib
        with contextlib.redirect_stderr(io.StringIO()):
            if not webbrowser.open(url):
                print("  (Browser bitte manuell oeffnen – siehe Adresse oben.)")
    except Exception:  # noqa: BLE001
        print("  (Browser bitte manuell oeffnen – siehe Adresse oben.)")


def main():
    parser = argparse.ArgumentParser(description="Token-Benchmark Web-UI")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-open", action="store_true", help="Browser nicht automatisch oeffnen")
    args = parser.parse_args()

    os.chdir(HERE)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://localhost:{args.port}"
    print(f"\n  Token-Benchmark UI laeuft auf  {url}")
    if _is_wsl():
        print("  (WSL erkannt – oeffne die Adresse im Windows-Browser, falls noetig)")
    print("  Zum Beenden: Strg+C\n")

    if not args.no_open:
        _open_browser(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server beendet.\n")
        server.shutdown()


if __name__ == "__main__":
    main()
