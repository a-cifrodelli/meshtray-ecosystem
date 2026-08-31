#!/bin/bash

# Vai nella cartella in cui risiede lo script
cd "$(dirname "$0")"

echo "=================================================="
echo "        Meshtray - Inizializzazione Client"
echo "=================================================="

# Verifica la presenza del venv
if [ ! -d ".venv" ]; then
    echo "[LAUNCH] Virtual environment non trovato. Creazione in corso..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "[ERRORE] Impossibile creare il virtual environment. Assicurati che Python sia installato."
        exit 1
    fi
    echo "[LAUNCH] Aggiornamento pip..."
    .venv/bin/python -m pip install --upgrade pip
fi

echo "[LAUNCH] Verifica e installazione dei requisiti..."
.venv/bin/pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[WARNING] Installazione dei pacchetti fallita o parziale."
fi

echo "[LAUNCH] Avvio di Meshtray in corso..."
.venv/bin/python main.py "$@"
