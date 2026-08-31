import sys
import os

# Aggiunge solo la cartella server al path di sistema per evitare collisioni con il client
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(project_root, "server"))

# Mock delle variabili d'ambiente per evitare errori all'avvio dei moduli del server
os.environ["MQTT_BROKER"] = "localhost"
os.environ["MQTT_USER"] = "test_user"
os.environ["MQTT_PASS"] = "test_pass"

# Sovrascriviamo l'URL del database per usare SQLite in memoria prima che i moduli lo carichino
import config
config.DATABASE_URL = "sqlite+aiosqlite:///:memory:"
