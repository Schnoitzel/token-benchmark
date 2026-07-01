# Basis: Node 24 (fuer pi + claude) mit schlankem Debian
FROM node:24-bookworm-slim

# Python 3 + git installieren (git fuer Repo-Reset-Funktion)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        git && \
    rm -rf /var/lib/apt/lists/*

# pi + claude global installieren
# claude.exe ist tatsaechlich ein ELF-Linux-Binary (~245 MB), npm-bin-Symlink zeigt darauf
RUN npm install -g --loglevel=error \
    @earendil-works/pi-coding-agent \
    @anthropic-ai/claude-code

# Projektcode hineinkopieren
WORKDIR /app
COPY *.py /app/
COPY static/ /app/static/

# Arbeitsverzeichnis fuer results/ (wird evtl. gemountet)
RUN mkdir -p /app/results

# Nicht-root-User verwenden (claude --allow-dangerously-skip-permissions funktioniert nicht als root)
# node-Image bringt bereits User 'node' (UID 1000) mit
RUN chown -R node:node /app
USER node

# Port fuer die UI
EXPOSE 8000

# Default: UI-Server starten
# Login-Daten in ~/... (via named volume persistent, jetzt als tokenbench-User)
CMD ["python3", "server.py", "--no-open"]
