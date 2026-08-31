import sys
import os

# Aggiunge solo la cartella client al path di sistema per evitare collisioni con il server
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(project_root, "client"))
