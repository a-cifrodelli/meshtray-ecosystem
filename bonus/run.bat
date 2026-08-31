@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "VENV=%SCRIPT_DIR%.venv"
set "PYTHON=%VENV%\Scripts\python.exe"
set "PIP=%VENV%\Scripts\pip.exe"
set "REQUIREMENTS=%SCRIPT_DIR%requirements.txt"

set "CMD=%~1"

if "%CMD%"==""          goto :usage
if /i "%CMD%"=="-h"     goto :usage
if /i "%CMD%"=="--help" goto :usage

rem Estrae tutti gli argomenti successivi al primo comando
for /f "tokens=1* delims= " %%A in ("%*") do (
    set "REST_ARGS=%%B"
)

if /i "%CMD%"=="midi"   goto :domidi
if /i "%CMD%"=="play"   goto :doplay

echo [ERROR] Comando non riconosciuto: %CMD%
goto :usage

:setup
if not exist "%PYTHON%" (
    echo [INFO] Creazione virtual environment in .venv ...
    python -m venv "%VENV%"
    if errorlevel 1 (
        echo [ERROR] Python non trovato o creazione venv fallita.
        exit /b 1
    )
    if exist "%REQUIREMENTS%" (
        echo [INFO] Installazione dipendenze ...
        "%PIP%" install --quiet -r "%REQUIREMENTS%"
        if errorlevel 1 (
            echo [ERROR] Installazione dipendenze fallita.
            exit /b 1
        )
    )
    echo [INFO] Setup completato.
)
goto :eof

:domidi
if "%REST_ARGS%"=="" (
    echo [ERROR] Parametri mancanti per il comando midi.
    goto :usage
)
call :setup
if errorlevel 1 exit /b 1
"%PYTHON%" "%SCRIPT_DIR%midi_2_rttl.py" !REST_ARGS!
exit /b %ERRORLEVEL%

:doplay
if "%REST_ARGS%"=="" (
    echo [ERROR] Parametri mancanti per il comando play.
    goto :usage
)
call :setup
if errorlevel 1 exit /b 1
"%PYTHON%" "%SCRIPT_DIR%rttl_sim.py" !REST_ARGS!
exit /b %ERRORLEVEL%

:usage
echo.
echo  Uso: run.bat ^<comando^> [argomenti...]
echo.
echo  Comandi:
echo    midi  ^<file.mid^> [--start SEC] [--end SEC] [--bpm N] [--track N]
echo    play  ^<stringa RTTTL^> ^| --file ^<suoneria.txt^> ^| --demo
echo.
exit /b 0