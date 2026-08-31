#!/bin/bash
cd "$(dirname "$0")"

VENV="server/.venv"

if [ ! -d "$VENV" ]; then
    echo "Creating virtual environment for server..."
    python3 -m venv $VENV
fi

echo "Activating server virtual environment..."
source $VENV/bin/activate

echo "Installing dependencies..."
python3 -m pip install --upgrade pip
pip install -r server/requirements.txt

echo "Running server tests..."
python3 -m pytest tests/test_server -v

echo "Deactivating environment..."
deactivate
