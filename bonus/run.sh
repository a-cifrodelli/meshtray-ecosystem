#!/usr/bin/env bash
# ============================================================
# run.sh — Launcher Linux per midi_2_rttl e rttl_sim
# Uso:
#   ./run.sh midi <file.mid> [opzioni]
#   ./run.sh play "NomeCanzone:d=4,o=5,b=120:..." [opzioni]
#   ./run.sh play --file ringtone.txt [opzioni]
#   ./run.sh play --demo
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
PYTHON="$VENV/bin/python"
PIP="$VENV/bin/pip"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"

# ── Help ──────────────────────────────────────────────────────
usage() {
    cat <<EOF

 Uso: ./run.sh <comando> [argomenti...]

 Comandi:
   midi  <file.mid> [--list-tracks] [--track N] [--auto-fit] [--transpose N]
                    [--start SEC] [--end SEC] [--bpm N] [--octave N]
                    [--duration N] [--name STR]
                    Converte un file MIDI in stringa RTTTL e la stampa.

   play  <stringa RTTTL> | --file <ringtone.txt> | --demo
                    [--wave sine|square|triangle] [--volume 0.0-1.0] [--fs HZ]
                    Riproduce una stringa RTTTL via audio di sistema.

 Esempi:
   ./run.sh midi canzone.mid --list-tracks
   ./run.sh midi canzone.mid --track 1 --auto-fit
   ./run.sh play --demo
   ./run.sh play "Mario:d=4,o=5,b=200:e6,e6,4p,e6,4p,c6,e6,4g6"
   ./run.sh play --file mia_suoneria.txt --wave square --volume 0.5

EOF
}

# ── Crea/aggiorna venv se necessario ─────────────────────────
ensure_venv() {
    if [ ! -f "$PYTHON" ]; then
        echo "[INFO] Creazione virtual environment in .venv ..."
        python3 -m venv "$VENV"
        if [ -f "$REQUIREMENTS" ]; then
            echo "[INFO] Installazione dipendenze da requirements.txt ..."
            "$PIP" install --quiet -r "$REQUIREMENTS"
        fi
        echo "[INFO] Setup completato."
    elif [ -f "$REQUIREMENTS" ] && [ "$REQUIREMENTS" -nt "$PYTHON" ]; then
        echo "[INFO] requirements.txt aggiornato, reinstallazione dipendenze ..."
        "$PIP" install --quiet -r "$REQUIREMENTS"
    fi
}

# ── Dispatch ──────────────────────────────────────────────────
CMD="${1:-}"

case "$CMD" in
    midi)
        shift
        if [ "$#" -eq 0 ]; then
            echo "[ERROR] Parametri mancanti per il comando midi."
            usage
            exit 1
        fi
        ensure_venv
        exec "$PYTHON" "$SCRIPT_DIR/midi_2_rttl.py" "$@"
        ;;
    play)
        shift
        if [ "$#" -eq 0 ]; then
            echo "[ERROR] Parametri mancanti per il comando play."
            usage
            exit 1
        fi
        ensure_venv
        exec "$PYTHON" "$SCRIPT_DIR/rttl_sim.py" "$@"
        ;;
    -h|--help|"")
        usage
        exit 0
        ;;
    *)
        echo "[ERROR] Comando non riconosciuto: $CMD"
        usage
        exit 1
        ;;
esac