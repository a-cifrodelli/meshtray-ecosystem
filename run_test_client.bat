@echo off
cd /d "%~dp0"

set VENV=client\.venv

if not exist %VENV% (
    echo Creating virtual environment for client...
    python -m venv %VENV%
    if errorlevel 1 (
        echo Error: Python is not installed or not in PATH.
        exit /b 1
    )
)

echo Activating client virtual environment...
call %VENV%\Scripts\activate.bat

echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r client\requirements.txt

echo Running client tests...
python -m pytest tests/test_client -v

echo Deactivating environment...
call deactivate
