#!/bin/bash
cd "$(dirname "$0")"

VENV="client/.venv"

if [ ! -d "$VENV" ]; then
    echo "Creating virtual environment for client..."
    python3 -m venv $VENV
fi

echo "Activating client virtual environment..."
source $VENV/bin/activate

echo "Installing dependencies..."
python3 -m pip install --upgrade pip
pip install -r client/requirements.txt

echo "Running client tests..."
python3 -m pytest tests/test_client -v

echo "Deactivating environment..."
deactivate
