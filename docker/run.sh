#!/usr/bin/env bash
# Wrapper-Skripte fuer den Token-Benchmark-Container
# Kommunikation auf Deutsch

set -euo pipefail

IMAGE_NAME="token-benchmark"
VOLUME_NAME="tokenbench-creds"
CONTAINER_HOME="/home/node"  # Home-Dir des nicht-root-Users im Container (node-Image: UID 1000)

# --- Funktionen ---

usage() {
    cat <<EOF
Verwendung: $0 <command>

Befehle:
  import-creds  Host-Credentials (Pi + Claude) ins Volume kopieren (empfohlen)
  login         OAuth-Login für Pi und Claude Code (interaktiv im Container)
  ui            UI-Server starten (http://localhost:8000)
  bench         Benchmark fahren (Standard: medium-bash, n=10)
  shell         Shell im Container (für Debugging)

Beispiele:
  $0 import-creds          # Host-Login ins Volume kopieren (einfachster Weg)
  $0 login                 # interaktiver Login im Container (umständlich)
  $0 ui
  $0 bench                 # medium-bash, n=10, alle Modelle
  $0 bench --repeat 5      # medium-bash, n=5
  $0 bench --tasks simple-code --repeat 3

Die Login-Daten (OAuth) werden im named volume "$VOLUME_NAME" persistent 
gespeichert und gehen nicht bei Container-Neustarts verloren.
EOF
    exit 0
}

# Prüfen ob Image existiert
check_image() {
    if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
        echo "❌ Image '$IMAGE_NAME' nicht gefunden."
        echo "   Bitte zuerst bauen: docker build -t $IMAGE_NAME ."
        exit 1
    fi
}

# Host-Credentials ins Volume kopieren (empfohlener Weg)
do_import_creds() {
    check_image
    echo "📦 Importiere Host-Credentials ins Volume '$VOLUME_NAME'..."
    echo ""
    
    # Prüfen ob Host-Pi-Login existiert
    if [[ ! -f "$HOME/.pi/agent/auth.json" ]]; then
        echo "❌ Keine Pi-Credentials auf dem Host gefunden."
        echo "   Bitte zuerst 'pi' auf dem Host starten und einloggen (Befehl /login im TUI)."
        exit 1
    fi
    
    # Prüfen ob Host-Claude-Login existiert
    if [[ ! -f "$HOME/.claude/.credentials.json" ]]; then
        echo "⚠️  Keine Claude-Credentials auf dem Host gefunden."
        echo "   Falls Claude genutzt werden soll: 'claude auth login' auf dem Host ausführen."
        echo "   Fahre nur mit Pi-Credentials fort..."
        echo ""
    fi
    
    # Pi-Credentials kopieren
    echo "1️⃣  Kopiere Pi-Credentials (~/.pi/agent/)..."
    docker run --rm \
        -v "$VOLUME_NAME:$CONTAINER_HOME" \
        -v "$HOME/.pi/agent:/host-pi:ro" \
        busybox \
        sh -c "mkdir -p $CONTAINER_HOME/.pi && cp -r /host-pi $CONTAINER_HOME/.pi/agent && chown -R 1000:1000 $CONTAINER_HOME/.pi"
    
    # Claude-Credentials kopieren (falls vorhanden)
    if [[ -f "$HOME/.claude/.credentials.json" ]]; then
        echo "2️⃣  Kopiere Claude-Credentials (~/.claude/ + ~/.claude.json)..."
        # Verzeichnis ~/.claude/ kopieren
        docker run --rm \
            -v "$VOLUME_NAME:$CONTAINER_HOME" \
            -v "$HOME/.claude:/host-claude:ro" \
            busybox \
            sh -c "mkdir -p $CONTAINER_HOME/.claude && cp -r /host-claude/. $CONTAINER_HOME/.claude/ && chown -R 1000:1000 $CONTAINER_HOME/.claude"
        # Datei ~/.claude.json kopieren (falls vorhanden)
        if [[ -f "$HOME/.claude.json" ]]; then
            docker run --rm \
                -v "$VOLUME_NAME:$CONTAINER_HOME" \
                -v "$HOME/.claude.json:/host-claude.json:ro" \
                busybox \
                sh -c "cp /host-claude.json $CONTAINER_HOME/.claude.json && chown 1000:1000 $CONTAINER_HOME/.claude.json"
        fi
    fi
    
    echo ""
    echo ""
    echo "✅ Credentials erfolgreich importiert."
    echo "   Testen mit: $0 shell  →  pi -p 'sage OK' --mode json --no-session"
}

# Login (interaktiv im Container): Pi + Claude nacheinander
# ACHTUNG: Headless-Login ist umständlich – siehe README für Details.
do_login() {
    check_image
    echo "🔐 Interaktiver OAuth-Login für Pi und Claude Code..."
    echo "    (Login-Daten werden in Volume '$VOLUME_NAME' gespeichert)"
    echo ""
    echo "⚠️  HINWEIS: Headless-Login ist umständlich."
    echo "   Empfohlen: Zuerst auf dem Host einloggen, dann '$0 import-creds' nutzen."
    echo ""
    read -p "Trotzdem fortfahren? (j/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Jj]$ ]]; then
        echo "Abgebrochen."
        exit 0
    fi
    
    # Pi-Login (interaktiver TUI)
    echo ""
    echo "1️⃣  Pi-Login..."
    echo "   Starte Pi im interaktiven Modus. Gib den Befehl '/login' ein und folge den Anweisungen."
    echo "   (Zum Beenden nach erfolgreichem Login: /exit)"
    echo ""
    read -p "Bereit? (Enter drücken)" _
    docker run --rm -it \
        -v "$VOLUME_NAME:$CONTAINER_HOME" \
        "$IMAGE_NAME" \
        pi
    
    echo ""
    echo "2️⃣  Claude-Login..."
    echo "   Öffne den angezeigten Link im Browser und folge den Anweisungen."
    echo ""
    read -p "Bereit? (Enter drücken)" _
    docker run --rm -it \
        -v "$VOLUME_NAME:$CONTAINER_HOME" \
        "$IMAGE_NAME" \
        claude auth login
    
    echo ""
    echo "✅ Login abgeschlossen. Die Credentials sind jetzt persistent im Volume gespeichert."
}

# UI starten (Port 8000)
do_ui() {
    check_image
    echo "🚀 Starte UI-Server auf http://localhost:8000 ..."
    echo "   (Zum Beenden: Strg+C)"
    echo ""
    docker run --rm -it \
        -v "$VOLUME_NAME:$CONTAINER_HOME" \
        -v "$(pwd)/results:/app/results" \
        -p 8000:8000 \
        "$IMAGE_NAME"
}

# Benchmark fahren (CLI)
do_bench() {
    check_image
    # Default: medium-bash, n=10
    local args=("--tasks" "medium-bash" "--repeat" "10")
    
    # User-Argumente ueberschreiben den Default
    if [[ $# -gt 0 ]]; then
        args=("$@")
    fi
    
    echo "🔬 Fahre Benchmark: python3 main.py ${args[*]}"
    echo ""
    docker run --rm -it \
        -v "$VOLUME_NAME:$CONTAINER_HOME" \
        -v "$(pwd)/results:/app/results" \
        "$IMAGE_NAME" \
        python3 main.py "${args[@]}"
    
    echo ""
    echo "✅ Benchmark abgeschlossen. Ergebnisse in ./results/"
}

# Shell im Container (Debugging)
do_shell() {
    check_image
    echo "🐚 Starte Shell im Container..."
    docker run --rm -it \
        -v "$VOLUME_NAME:$CONTAINER_HOME" \
        -v "$(pwd)/results:/app/results" \
        "$IMAGE_NAME" \
        /bin/bash
}

# --- Main ---

if [[ $# -eq 0 ]]; then
    usage
fi

case "$1" in
    import-creds)
        do_import_creds
        ;;
    login)
        do_login
        ;;
    ui)
        do_ui
        ;;
    bench)
        shift  # "bench" entfernen
        do_bench "$@"
        ;;
    shell)
        do_shell
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        echo "❌ Unbekannter Befehl: $1"
        echo ""
        usage
        ;;
esac
