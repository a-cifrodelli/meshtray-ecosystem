@echo off
setlocal enabledelayedexpansion

:: Vai nella cartella in cui risiede lo script
cd /d "%~dp0"

echo ==================================================
echo         Meshtray - Inizializzazione Client
echo ==================================================

:: Verifica la presenza del venv
if not exist ".venv" (
    echo [LAUNCH] Virtual environment non trovato. Creazione in corso...
    python -m venv .venv
    if !errorlevel! neq 0 (
        echo [ERRORE] Impossibile creare il virtual environment. Assicurati che Python sia nel PATH.
        pause
        exit /b 1
    )
    echo [LAUNCH] Aggiornamento pip...
    .venv\Scripts\python.exe -m pip install --upgrade pip
)

echo [LAUNCH] Verifica e installazione dei requisiti...
.venv\Scripts\pip.exe install -r requirements.txt
if !errorlevel! neq 0 (
    echo [WARNING] Installazione dei pacchetti fallita o parziale.
)

echo [LAUNCH] Avvio di Meshtray in corso...
.venv\Scripts\python.exe main.py %*

if %errorlevel% neq 0 (
    echo [LAUNCH] L'applicazione si e arrestata con un errore.
    pause
)
