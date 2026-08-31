import asyncio
from asyncio_paho import AsyncioPahoClient
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import config as c

# ===== Globals =======
send_queue = asyncio.Queue(maxsize=c.QUEUEMAXSIZE)
mqtt_client: AsyncioPahoClient = None

iface = None
serial_lock = asyncio.Lock()

ws_app = FastAPI()
ws_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)
ws_clients = set()
history_clients = set()
ws_server = None
worker_task = None
ws_server_task = None
device_debug = False
serial_release_task = None
radio_monitor_task = None
