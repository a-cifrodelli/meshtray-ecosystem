import os
import ssl
import json
import asyncio
import random
import datetime
import pytz
import websockets
from PyQt6.QtCore import QThread, pyqtSignal
from config import *

class ConnectionThread(QThread):
    # Signals to communicate thread-safely with the PyQt6 main thread
    message_received = pyqtSignal(str, str, str, str, str)  # ts, from, to, channel, text
    archive_message_received = pyqtSignal(str, str, str, str, str)  # ts, from, to, channel, text
    connection_status_changed = pyqtSignal(bool)
    archive_load_finished = pyqtSignal(bool)  # is_last_page
    
    # New Signals for Chat & Navigation
    nodes_channels_received = pyqtSignal(list, list, bool)  # list of nodes, list of channels, radio_online
    chat_history_received = pyqtSignal(str, str, str, str, str)  # ts, from, to, channel, text
    chat_load_finished = pyqtSignal(bool)  # is_last_page
    message_sent_status = pyqtSignal(bool, str)  # success, error_message

    def __init__(self, is_mock=False, mock_delay=3.0, parent=None):
        super().__init__(parent)
        self.is_mock = is_mock
        self.mock_delay = mock_delay
        self.loop = None
        self.stop_event = None
        self.active_tasks = []

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.stop_event = asyncio.Event()

        if self.is_mock:
            self.loop.run_until_complete(self._run_mock_loop())
        else:
            self.loop.run_until_complete(self._run_real_loop())

    async def _run_mock_loop(self):
        self.connection_status_changed.emit(True)
        
        # Background task for live mock messages
        async def mock_generator():
            nodes = ["!a1b2c3d4", "!deadbeef", "!cafebabe", "!12345678", "!f00dface"]
            texts = [
                "Ciao a tutti dalla mesh!",
                "Segnale ottimo qui.",
                "Qualcuno riceve?",
                "Test 1 2 3",
                "Nodo attivo – tutto ok",
                "Posizione aggiornata",
                "Batteria al 87%",
                "Connessione stabile",
                "RSSI: -{} dBm",
                "SNR: {:.1f} dB",
                "Messaggio lungo per testare l'auto-wrapping di QLabel all'interno del feed di PyQt6.",
            ]
            while not self.stop_event.is_set():
                await asyncio.sleep(self.mock_delay)
                if self.stop_event.is_set():
                    break
                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                from_node = random.choice(nodes)
                to_node = random.choice(["local_node", "^all", "^all"])
                text = random.choice(texts)
                try:
                    text = text.format(random.randint(60, 130), random.uniform(-5, 15))
                except Exception:
                    pass
                self.message_received.emit(ts, from_node, to_node, "LongFast" if to_node == "^all" else "DM", text)

        task = asyncio.create_task(mock_generator())
        self.active_tasks.append(task)
        await self.stop_event.wait()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def _run_real_loop(self):
        async def listen_notifications():
            while not self.stop_event.is_set():
                try:
                    ssl_context = self._get_ssl_context(WS_URL_NOTIFICATION)
                    print(f"[Connection] Connessione a {WS_URL_NOTIFICATION}")
                    async with websockets.connect(WS_URL_NOTIFICATION, ssl=ssl_context) as ws:
                        self.connection_status_changed.emit(True)
                        asyncio.create_task(self._fetch_nodes_channels())
                        while not self.stop_event.is_set():
                            data = await ws.recv()
                            payload = json.loads(data)

                            # Gestione pacchetti di stato hardware radio (push real-time)
                            if payload.get("type") == "radio_status":
                                radio_online = payload.get("radio_online", False)
                                nodes = payload.get("nodes", [])
                                channels = payload.get("channels", [])
                                self.nodes_channels_received.emit(nodes, channels, radio_online)
                                if radio_online:
                                    # Richiede una sincronizzazione completa di canali e NodeDB
                                    asyncio.create_task(self._fetch_nodes_channels())
                                continue

                            ts = payload.get("timestamp", 0)
                            dt_str = self.epoch_to_datetime_str(ts)
                            from_ = payload.get("from", "unknown")
                            to_ = payload.get("to", "")
                            channel = payload.get("channel", "default")
                            p = payload.get("payload", {})
                            if isinstance(p, dict):
                                text = p.get("text", "") or payload.get("text", "")
                            elif isinstance(p, str):
                                text = p or payload.get("text", "")
                            else:
                                text = payload.get("text", "")
                            self.message_received.emit(dt_str, from_, to_, channel, text)
                except websockets.ConnectionClosed:
                    self.connection_status_changed.emit(False)
                except Exception as e:
                    self.connection_status_changed.emit(False)
                    print(f"[Connection] Errore socket: {e}")
                
                if not self.stop_event.is_set():
                    await asyncio.sleep(3)

        task = asyncio.create_task(listen_notifications())
        self.active_tasks.append(task)
        await self.stop_event.wait()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    def request_archive_page(self, offset, limit):
        if self.is_mock:
            self._generate_mock_archive(offset, limit)
        else:
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(self._fetch_archive_page(offset, limit), self.loop)

    def _generate_mock_archive(self, offset, limit):
        nodes = ["!a1b2c3d4", "!deadbeef", "!cafebabe", "!12345678", "!f00dface"]
        channels = ["LongFast", "MediumSlow", "ShortFast", "LongSlow"]
        texts = [
            "Storico: messaggio ricevuto in passato.",
            "Test connessione mesh riuscito.",
            "Report telemetria: OK",
            "Batteria remote node al 92%",
            "Ping di verifica",
        ]
        now = datetime.datetime.now()
        for i in range(limit):
            dt_obj = now - datetime.timedelta(seconds=(offset + i) * 20)
            dt_str = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
            from_node = random.choice(nodes)
            to_node = random.choice(nodes + ["^all"])
            channel = random.choice(channels)
            text = random.choice(texts)
            self.archive_message_received.emit(dt_str, from_node, to_node, channel, text)
            
        is_last = (offset + limit) >= 1000
        self.archive_load_finished.emit(is_last)

    async def _fetch_archive_page(self, offset, limit):
        try:
            ssl_context = self._get_ssl_context(WS_URL_HISTORY)
            async with websockets.connect(WS_URL_HISTORY, ssl=ssl_context) as ws:
                req = {"action": "get", "offset": offset, "limit": limit}
                await ws.send(json.dumps(req))
                response = await ws.recv()
                data = json.loads(response)
                msgs = data.get("messages", [])
                
                for msg in msgs:
                    ts_iso = msg.get("timestamp", "")
                    dt_str = self.iso_to_local_str(ts_iso)
                    from_ = msg.get("sender", "")
                    to_ = msg.get("dest", "")
                    channel = msg.get("channel", "")
                    text = msg.get("text", "")
                    self.archive_message_received.emit(dt_str, from_, to_, channel, text)
                
                is_last = len(msgs) < limit
                self.archive_load_finished.emit(is_last)
        except Exception as e:
            print(f"[Connection Archive] Errore caricamento archivio: {e}")
            self.archive_load_finished.emit(True)

    def request_chat_history(self, offset, limit, filter_target=None, filter_channel=None):
        if self.is_mock:
            self._generate_mock_chat_history(offset, limit, filter_target, filter_channel)
        else:
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._fetch_chat_history(offset, limit, filter_target, filter_channel),
                    self.loop
                )

    def request_nodes_channels(self):
        if self.is_mock:
            mock_nodes = ["!a1b2c3d4", "!deadbeef", "!cafebabe", "!12345678", "!f00dface"]
            mock_channels = ["LongFast", "MediumSlow", "ShortFast", "LongSlow"]
            self.nodes_channels_received.emit(mock_nodes, mock_channels, True)
        else:
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(self._fetch_nodes_channels(), self.loop)

    def send_message(self, text, to_node=None, channel=None):
        if self.is_mock:
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.message_sent_status.emit(True, "")
            self.message_received.emit(ts, "local_node", to_node if to_node else "^all", "DM" if to_node else (channel if channel else "default"), text)
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(self._mock_reply_delayed(text, to_node, channel), self.loop)
        else:
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(self._send_message_ws(text, to_node, channel), self.loop)

    async def _mock_reply_delayed(self, text, to_node, channel):
        import random
        # Delay between 1.5 and 3.0 seconds
        await asyncio.sleep(random.uniform(1.5, 3.0))
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        replies = [
            "Ricevuto forte e chiaro!",
            f"Copia conforme del messaggio: '{text}'",
            "Qui il segnale è ottimo, RSSI: -85dBm.",
            "Ok, confermo la ricezione.",
            "Ottimo! Tutto attivo sulla mesh.",
            "Ricezione corretta, ciao!",
            "Messaggio letto con successo."
        ]
        reply_text = random.choice(replies)
        
        if to_node:
            # private reply (DM)
            self.message_received.emit(ts, to_node, "local_node", "DM", reply_text)
        else:
            # channel reply
            nodes = ["!a1b2c3d4", "!deadbeef", "!cafebabe", "!12345678", "!f00dface"]
            other_node = random.choice(nodes)
            chan = channel if channel else "LongFast"
            self.message_received.emit(ts, other_node, "^all", chan, reply_text)

    def _generate_mock_chat_history(self, offset, limit, filter_target, filter_channel):
        now = datetime.datetime.now()
        target_name = filter_target if filter_target else (filter_channel if filter_channel else "Global")
        for i in range(limit):
            dt_obj = now - datetime.timedelta(seconds=(offset + i) * 60)
            dt_str = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
            if i % 2 == 0:
                from_node = "local_node"
                to_node = filter_target if filter_target else "^all"
            else:
                from_node = filter_target if filter_target else "!deadbeef"
                to_node = "local_node" if filter_target else "^all"

            text = f"Messaggio {offset + i + 1} per {target_name}."
            chan = filter_channel if filter_channel else "DM"
            self.chat_history_received.emit(dt_str, from_node, to_node, chan, text)

        is_last = (offset + limit) >= 200
        self.chat_load_finished.emit(is_last)

    async def _fetch_chat_history(self, offset, limit, filter_target, filter_channel):
        try:
            ssl_context = self._get_ssl_context(WS_URL_HISTORY)
            async with websockets.connect(WS_URL_HISTORY, ssl=ssl_context) as ws:
                req = {
                    "action": "get",
                    "offset": offset,
                    "limit": limit,
                    "filter_target": filter_target,
                    "filter_channel": filter_channel
                }
                await ws.send(json.dumps(req))
                response = await ws.recv()
                data = json.loads(response)
                msgs = data.get("messages", [])

                for msg in msgs:
                    ts_iso = msg.get("timestamp", "")
                    dt_str = self.iso_to_local_str(ts_iso)
                    from_ = msg.get("sender", "")
                    to_ = msg.get("dest", "")
                    channel = msg.get("channel", "")
                    text = msg.get("text", "")
                    self.chat_history_received.emit(dt_str, from_, to_, channel, text)

                is_last = len(msgs) < limit
                self.chat_load_finished.emit(is_last)
        except Exception as e:
            print(f"[Connection Chat History] Errore: {e}")
            self.chat_load_finished.emit(True)

    async def _fetch_nodes_channels(self):
        try:
            ssl_context = self._get_ssl_context(WS_URL_NODES)
            async with websockets.connect(WS_URL_NODES, ssl=ssl_context) as ws:
                response = await ws.recv()
                data = json.loads(response)
                nodes = data.get("nodes", [])
                channels = data.get("channels", [])
                radio_online = data.get("radio_online", False)
                self.nodes_channels_received.emit(nodes, channels, radio_online)
        except Exception as e:
            print(f"[Connection Nodes/Channels] Errore: {e}")
            self.nodes_channels_received.emit([], [], False)

    async def _send_message_ws(self, text, to_node, channel):
        try:
            ssl_context = self._get_ssl_context(WS_URL_SEND)
            async with websockets.connect(WS_URL_SEND, ssl=ssl_context) as ws:
                req = {
                    "text": text,
                    "to": to_node if to_node else "",
                    "channel": channel if channel else "default"
                }
                await ws.send(json.dumps(req))
                resp_data = await ws.recv()
                resp = json.loads(resp_data)
                if resp.get("status") == "success":
                    self.message_sent_status.emit(True, "")
                else:
                    self.message_sent_status.emit(False, resp.get("message", "Unknown error"))
        except Exception as e:
            print(f"[Connection Send] Errore invio: {e}")
            self.message_sent_status.emit(False, str(e))

    def _get_ssl_context(self, url):
        if url.startswith("wss://"):
            if ROOT_CA and os.path.exists(ROOT_CA):
                return ssl.create_default_context(cafile=ROOT_CA)
            elif ROOT_CA:
                print(f"[Connection] WARNING: File ROOT_CA '{ROOT_CA}' non trovato, procedo con certificato di sistema.")
        return None

    def stop(self):
        if self.loop and self.stop_event:
            # Segnala alle coroutine di terminare tramite l'event
            self.loop.call_soon_threadsafe(self.stop_event.set)
        self.wait()

    def epoch_to_datetime_str(self, epoch):
        timezone = pytz.timezone(TZ)
        dt = datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).astimezone(timezone)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def iso_to_local_str(self, iso_str):
        try:
            dt = datetime.datetime.fromisoformat(iso_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=pytz.UTC)
            local_tz = pytz.timezone(TZ)
            dt_local = dt.astimezone(local_tz)
            return dt_local.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return iso_str
