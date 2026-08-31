#!/bin/bash

# Vai nella cartella in cui risiede lo script
cd "$(dirname "$0")"

echo "=================================================="
echo "        Meshtray - Compilatore Linux"
echo "=================================================="

# Verifica la presenza del venv e lo crea se manca
if [ ! -d ".venv" ]; then
    echo "[BUILDER] Virtual environment venv non trovato. Creazione in corso..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "[ERRORE] Impossibile creare il virtual environment. Assicurati che python3-venv sia installato."
        exit 1
    fi
    echo "[BUILDER] Aggiornamento pip..."
    .venv/bin/python -m pip install --upgrade pip
fi

echo "[BUILDER] Attivazione ambiente virtuale..."
source .venv/bin/activate

echo "[BUILDER] Verifica dei moduli necessari..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[WARNING] Installazione dipendenze fallita o parziale, provo comunque a compilare..."
fi

# Installa pyinstaller nel venv se non è presente
pip install pyinstaller

echo "[BUILDER] Compilazione con PyInstaller..."
# Su Linux, PyInstaller usa il separatore ':' per --add-data
pyinstaller --clean --noconsole --onefile --icon=asset/logo-app.png --add-data "asset/*:asset" --name=Meshtray main.py

if [ $? -eq 0 ]; then
    echo "[BUILDER] Compilazione completata con successo."
    echo "[BUILDER] Sposto il binario Meshtray nella cartella client..."
    mv dist/Meshtray ./Meshtray
    if [ $? -eq 0 ]; then
        rm -rf dist build
        echo "=================================================="
        echo "  SUCCESSO! Puoi eseguire './Meshtray' direttamente"
        echo "  dalla cartella client/ del progetto."
        echo "=================================================="
    else
        echo "[ERRORE] Impossibile spostare il file compilato nella cartella client/."
    fi
else
    echo "[ERRORE] Compilazione fallita. Controlla gli errori di PyInstaller."
fi
