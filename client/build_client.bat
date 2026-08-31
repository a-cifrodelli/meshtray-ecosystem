@echo off
setlocal enabledelayedexpansion

:: Vai nella cartella in cui risiede lo script
cd /d "%~dp0"

echo ==================================================
echo         Meshtray - Compilatore Eseguibile (.exe)
echo ==================================================

:: Verifica la presenza del venv e lo crea se manca
if not exist ".venv" (
    echo [BUILDER] Virtual environment venv non trovato. Creazione in corso...
    python -m venv .venv
    if !errorlevel! neq 0 (
        echo [ERRORE] Impossibile creare il virtual environment. Assicurati che Python sia nel PATH.
        pause
        exit /b 1
    )
    echo [BUILDER] Aggiornamento pip...
    .venv\Scripts\python.exe -m pip install --upgrade pip
)

echo [BUILDER] Attivazione ambiente virtuale...
call .venv\Scripts\activate.bat

echo "[BUILDER] Verifica dei moduli necessari..."
.venv\Scripts\pip.exe install -r requirements.txt
if !errorlevel! neq 0 (
    echo "[WARNING] Installazione dipendenze fallita, provo comunque a compilare..."
)

echo [BUILDER] Compilazione con PyInstaller...
pyinstaller --clean --noconsole --onefile --icon=asset\logo-app.ico --add-data "asset\*;asset" --name=Meshtray main.py

if !errorlevel! == 0 (
    echo [BUILDER] Compilazione completata con successo.
    echo [BUILDER] Sposto Meshtray.exe nella cartella client...
    move /y dist\Meshtray.exe .\Meshtray.exe
    if !errorlevel! == 0 (
        rmdir /s /q dist
        rmdir /s /q build
        echo ==================================================
        echo   SUCCESSO! Puoi eseguire 'Meshtray.exe' direttamente
        echo   dalla cartella client/ del progetto.
        echo ==================================================
    ) else (
        echo [ERRORE] Impossibile spostare il file compilato nella cartella client/.
    )
) else (
    echo [ERRORE] Compilazione fallita. Controlla gli errori di PyInstaller.
)

pause
