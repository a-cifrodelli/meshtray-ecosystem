@echo off
cd /d "%~dp0"

set VENV=server\.venv

if not exist %VENV% (
    echo Creating virtual environment for server...
    python -m venv %VENV%
    if errorlevel 1 (
        echo Error: Python is not installed or not in PATH.
        exit /b 1
    )
)

echo Activating server virtual environment...
call %VENV%\Scripts\activate.bat

echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r server\requirements.txt

echo Running server tests...
python -m pytest tests/test_server -v

echo Deactivating environment...
call deactivate
