import os
from dotenv import load_dotenv, find_dotenv

# Resolve dynamic paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)

load_dotenv(find_dotenv())

# ===== Configurazioni =====
MQTT_BROKER = os.getenv("MQTT_BROKER", "")
MQTT_PORT = 8883
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASS = os.getenv("MQTT_PASS", "")
MQTT_TOPIC_IN = "msh/#"    # tutti i messaggi dai nodi
MQTT_TOPIC_OUT = "meshtastic/outgoing"
WS_HOST = "0.0.0.0"
WS_PORT = 8088
IGNORED_CHANNELS = {"2"} # numerici, l'id del canale nella configurazione
QUEUE_MAXSIZE = 50
DEFAULT_DB_PATH = os.path.join(PROJECT_DIR, "data", "meshtastic.db")
DATABASE_PATH = os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{DATABASE_PATH}")
MESHTASTIC_SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/ttyUSB0")
DELAY_BETWEEN_SENDS = 0.2
SERIAL_KEEP_ALIVE = 10
QUEUEMAXSIZE = 50
QUEUEFULLTOPIC = "/meshtastic/waiting"
MQTT_CA_CERTS = os.getenv("MQTT_CA_CERTS", os.path.join(PROJECT_DIR, "certs", "root_ca.crt"))
