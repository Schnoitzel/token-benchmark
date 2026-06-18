"""
Benchmark-Aufgaben, sortiert nach Komplexitaet.

Alle Prompts sind absichtlich in sich geschlossen, damit beide Harnesses
ohne Projektkontext eine gueltige Antwort liefern.

  use_tools=False -> Modell soll aus Wissen antworten
  use_tools=True  -> Modell soll Shell-/Datei-Tools benutzen
"""

from dataclasses import dataclass


@dataclass
class Task:
    id: str
    complexity: str  # "trivial" | "simple" | "medium" | "complex"
    description: str
    prompt: str
    use_tools: bool


TASKS: list[Task] = [
    # --- Baseline ----------------------------------------------------------
    # Trivial-Prompt zur DIREKTEN Messung des reinen Harness-Overheads.
    # Die Antwort ist winzig, daher sind input + cache_read + cache_write
    # praktisch nur der System-Prompt + die Tool-Definitionen, die jeder
    # Harness bei JEDER Anfrage mitschickt - unabhaengig von Aufgabe und
    # Antwortlaenge. Das ist die unangreifbarste Overhead-Kennzahl.
    Task(
        id="baseline-overhead",
        complexity="baseline",
        description="Reiner Harness-Overhead (System-Prompt + Tool-Definitionen)",
        prompt="Reply with exactly: OK",
        use_tools=False,
    ),

    # --- Trivial -----------------------------------------------------------
    Task(
        id="trivial-fact",
        complexity="trivial",
        description="Einzelne Faktenfrage - keine Tools erwartet",
        prompt="In which year did the Berlin Wall fall? Answer in one sentence.",
        use_tools=False,
    ),
    Task(
        id="trivial-math",
        complexity="trivial",
        description="Einfache Rechnung - keine Tools erwartet",
        prompt="What is 17 x 23? Show your working in two lines.",
        use_tools=False,
    ),

    # --- Simple ------------------------------------------------------------
    Task(
        id="simple-code",
        complexity="simple",
        description="Kurze eigenstaendige Funktion schreiben - keine Tools erwartet",
        prompt=(
            "Write a TypeScript function called `debounce` that delays invoking a "
            "callback until after `waitMs` milliseconds have elapsed since the last "
            "call. Include the function signature with generics and a brief JSDoc "
            "comment. No imports needed."
        ),
        use_tools=False,
    ),
    Task(
        id="simple-explain",
        complexity="simple",
        description="Knappe technische Erklaerung - keine Tools erwartet",
        prompt=(
            "Explain the difference between `Promise.all()` and "
            "`Promise.allSettled()` in JavaScript. Use a bullet list with max 4 points."
        ),
        use_tools=False,
    ),

    # --- Medium ------------------------------------------------------------
    Task(
        id="medium-design",
        complexity="medium",
        description="API-Design - keine Tools erwartet",
        prompt=(
            "Design a minimal REST API for a todo-list application. List the "
            "endpoints (method + path), the JSON request/response shape for each, "
            "and two common error responses. Keep it under 200 words."
        ),
        use_tools=False,
    ),
    Task(
        id="medium-bash",
        complexity="medium",
        description="Shell-Aufgabe - Tool-Nutzung erwartet",
        prompt=(
            "Using the available shell tools, find the 5 largest files (by size) "
            "under /usr/share/doc and print their paths and sizes. Then summarise "
            "what you found in one sentence."
        ),
        use_tools=True,
    ),

    # --- Complex -----------------------------------------------------------
    Task(
        id="complex-refactor",
        complexity="complex",
        description="Code-Review & Refactoring-Plan - keine Tools erwartet",
        prompt=(
            "Review the following Python snippet and provide:\n"
            "1. A list of at least 3 concrete issues (correctness, style, performance).\n"
            "2. A refactored version that fixes all of them.\n"
            "3. A one-sentence explanation of the most important change.\n\n"
            "```python\n"
            "def get_user_data(ids):\n"
            "    result = []\n"
            "    for id in ids:\n"
            "        r = requests.get(\"https://api.example.com/users/\" + id)\n"
            "        data = r.json()\n"
            "        result.append(data)\n"
            "    return result\n"
            "```"
        ),
        use_tools=False,
    ),
    Task(
        id="complex-analysis",
        complexity="complex",
        description="Architektur-Analyse - keine Tools erwartet",
        prompt=(
            "You are reviewing a system where a single PostgreSQL database serves "
            "both an OLTP web application (thousands of concurrent short "
            "transactions) and an OLAP reporting pipeline (long-running analytical "
            "queries). Describe three specific problems this causes and propose a "
            "concrete architectural solution for each, referencing real tools or "
            "patterns (e.g. read replicas, CQRS, materialised views). Keep your "
            "answer under 300 words."
        ),
        use_tools=False,
    ),
]
