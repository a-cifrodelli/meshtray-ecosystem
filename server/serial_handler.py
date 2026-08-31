import asyncio
import json
import os
from meshtastic import serial_interface
import globals as g
import config as c

# ===== Serial Interface Management (Persistent while plugged in) =====

async def acquire_serial():
    """Apre la connessione seriale permanente con la radio se non già attiva"""
    if g.iface is None:
        import sys
        debug_out = sys.stdout if g.device_debug else None
        print(f"[Mesh] Connessione seriale a {c.MESHTASTIC_SERIAL_PORT}...")
        g.iface = serial_interface.SerialInterface(c.MESHTASTIC_SERIAL_PORT, debugOut=debug_out)
        print("[Mesh] Connessione seriale stabilita con successo.")

async def release_serial():
    """Chiude in modo sicuro l'interfaccia seriale"""
    if g.iface:
        try:
            g.iface.close()
        except Exception:
            pass
        g.iface = None
        print("[Mesh] Connessione seriale rilasciata.")

async def send_to_mesh(payload_json):
    """Accoda il messaggio verso la mesh"""
    try:
        g.send_queue.put_nowait(payload_json)
    except asyncio.QueueFull:
        g.mqtt_client.publish(c.QUEUEFULLTOPIC, json.dumps(payload_json))
        print("[Translator] Coda piena, messaggio ripubblicato su waiting")

async def queue_worker():
    """Consumer della coda per inviare messaggi sulla mesh"""
    # Limite massimo payload LoRa (Meshtastic): 228 byte codificati UTF-8
    LORA_MAX_BYTES = 228

    while True:
        payload_json = await g.send_queue.get()
        if payload_json is None:
            break

        async with g.serial_lock:
            try:
                await acquire_serial()
                text = payload_json.get("text", "")
                target = payload_json.get("to")
                channel_index = payload_json.get("channel_index", 0)

                # Tronca il messaggio al limite LoRa codificando in UTF-8
                encoded = text.encode("utf-8")
                if len(encoded) > LORA_MAX_BYTES:
                    print(f"[Mesh] ⚠️ Messaggio troncato: {len(encoded)} byte > {LORA_MAX_BYTES} byte (limite LoRa)")
                    text = encoded[:LORA_MAX_BYTES].decode("utf-8", errors="ignore")

                if target:
                    g.iface.sendText(text, destinationId=target, channelIndex=channel_index)
                    print(f"[Mesh] Inviato unicast a {target} sul canale {channel_index}: {text}")
                else:
                    g.iface.sendText(text, channelIndex=channel_index)
                    print(f"[Mesh] Broadcast sul canale {channel_index}: {text}")
            except Exception as e:
                print(f"[Mesh] ❌ Errore invio messaggio via seriale: {e}")

        await asyncio.sleep(c.DELAY_BETWEEN_SENDS)
        g.send_queue.task_done()

async def get_radio_nodes_channels():
    """Interroga il modulo radio per recuperare i nodi del NodeDB e i canali configurati"""
    nodes = []
    channels = []
    radio_online = False
    
    try:
        async with g.serial_lock:
            await acquire_serial()
            if g.iface:
                radio_online = True
                # 1. Estrazione nodi dal NodeDB del modulo radio
                if g.iface.nodes:
                    my_node_id = None
                    if g.iface.myInfo and g.iface.myInfo.my_node_num:
                        my_node_id = f"!{g.iface.myInfo.my_node_num:08x}"

                    for node_num in g.iface.nodes.keys():
                        if isinstance(node_num, int):
                            node_id = f"!{node_num:08x}"
                        elif isinstance(node_num, str):
                            if node_num.startswith("!"):
                                node_id = node_num
                            elif node_num.isdigit():
                                node_id = f"!{int(node_num):08x}"
                            else:
                                node_id = node_num
                        else:
                            node_id = str(node_num)

                        if my_node_id and node_id == my_node_id:
                            continue

                        nodes.append(node_id)
                
                # 2. Estrazione canali configurati sul modulo radio
                if g.iface.localNode and getattr(g.iface.localNode, "channels", None):
                    for ch in g.iface.localNode.channels:
                        role = getattr(ch, "role", 0)
                        # role: 0 = DISABLED, 1 = PRIMARY, 2 = SECONDARY
                        if role != 0:
                            name = getattr(ch.settings, "name", "")
                            if not name:
                                if role == 1:
                                    name = "Primary"
                                else:
                                    ch_idx = getattr(ch, "index", len(channels))
                                    name = f"Channel {ch_idx}"
                            if name and name not in channels:
                                channels.append(name)
    except Exception as e:
        print(f"[Serial Query] Impossibile leggere dalla radio (offline/non connessa): {e}")

    # Nessun fallback finto: se la radio non ha canali o non è connessa, restituisce liste vuote
    return sorted(list(set(nodes))), sorted(list(set(channels))), radio_online

async def check_radio_presence():
    """Verifica rapida e non bloccante della presenza fisica della porta seriale"""
    if not c.MESHTASTIC_SERIAL_PORT:
        return False
    if c.MESHTASTIC_SERIAL_PORT.startswith("/"):
        return os.path.exists(c.MESHTASTIC_SERIAL_PORT)
    else:
        try:
            import serial.tools.list_ports
            ports = [p.device.upper() for p in serial.tools.list_ports.comports()]
            return c.MESHTASTIC_SERIAL_PORT.upper() in ports
        except Exception:
            return False

async def radio_monitor():
    """Monitor in background per rilevare dinamicamente attacco/stacco della radio e notificare i client via WebSocket"""
    last_state = None
    while True:
        try:
            is_present = await check_radio_presence()
            if is_present:
                nodes, channels, radio_online = await get_radio_nodes_channels()
            else:
                if g.iface:
                    async with g.serial_lock:
                        await release_serial()
                nodes, channels, radio_online = [], [], False

            if radio_online != last_state:
                last_state = radio_online
                print(f"[Radio Monitor] Stato hardware radio: {'ONLINE 🟢' if radio_online else 'OFFLINE 🔴'}")
                payload = {
                    "type": "radio_status",
                    "radio_online": radio_online,
                    "nodes": nodes,
                    "channels": channels
                }
                import websocket_endpoints as ws_endpoints
                await ws_endpoints.broadcast_ws(payload)
        except asyncio.CancelledError:
            break
        except Exception as e:
            pass

        await asyncio.sleep(2)
