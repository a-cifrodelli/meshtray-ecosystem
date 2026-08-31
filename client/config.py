import os
import sys
from dotenv import load_dotenv, find_dotenv

# Caricamento del file .env (locale per sviluppo, accanto all'eseguibile per produzione)
if getattr(sys, 'frozen', False):
    _EXE_DIR = os.path.dirname(os.path.abspath(sys.executable))
    _ENV_PATH = os.path.join(_EXE_DIR, ".env")
    if os.path.exists(_ENV_PATH):
        load_dotenv(_ENV_PATH)
    else:
        load_dotenv(find_dotenv())
else:
    load_dotenv(find_dotenv())

MAX_MESSAGES = 200
TZ = "Europe/Rome"
ROOT_CA = os.getenv("ROOT_CA", "")
# URL di base del server WebSocket (es. ws://localhost:8088 o wss://192.168.1.50:8088)
WS_BASE_URL = os.getenv("WS_BASE_URL", "ws://localhost:8088").rstrip("/")

# Endpoint composti (con supporto a variabili specifiche per retrocompatibilità)
WS_URL_NOTIFICATION = os.getenv("WS_URL_NOTIFICATION", f"{WS_BASE_URL}/ws/notifications")
WS_URL_HISTORY = os.getenv("WS_URL_HISTORY", f"{WS_BASE_URL}/ws/history")
WS_URL_SEND = os.getenv("WS_URL_SEND", f"{WS_BASE_URL}/ws/send")
WS_URL_NODES = os.getenv("WS_URL_NODES", f"{WS_BASE_URL}/ws/nodes_channels")
TOAST_TIMEOUT = 4000
ARCHIVE_PAGE_SIZE = 200

# Risoluzione dei percorsi per sviluppo (.py) e produzione (.exe)
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # In modalità eseguibile monofile, gli asset incorporati vengono estratti in sys._MEIPASS
    _ROOT_DIR = sys._MEIPASS
elif getattr(sys, 'frozen', False):
    _ROOT_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    _ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

LOGO_APP_PNG = os.path.join(_ROOT_DIR, "asset", "logo-app.png")
TRAY_ICON_PNG = os.path.join(_ROOT_DIR, "asset", "tray-icon.png")
FAVICON_PNG = os.path.join(_ROOT_DIR, "asset", "logo-app.ico")
STARTING_BANNER_PNG = os.path.join(_ROOT_DIR, "asset", "starting_banner.png")
