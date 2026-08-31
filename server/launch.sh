#!/bin/bash
cd "$(dirname "$0")"

PYTHON="python"
PIP="$PYTHON -m pip"
VENV=".venv"

if [ ! -d $VENV ]; then
	$PYTHON -m venv $VENV
	source $VENV/bin/activate
	$PIP install -r requirements.txt
	deactivate
fi
source $VENV/bin/activate
$PYTHON main.py "$@"
deactivate
