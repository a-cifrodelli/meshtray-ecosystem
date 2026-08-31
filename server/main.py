import asyncio
from asyncio_paho import AsyncioPahoClient
import config as c
import globals as g
import mqtt_handler as mqtt
import serial_handler as serial
import db_engine as db
import websocket_endpoints as ws_endpoints

import tracemalloc

#tracemalloc.start()

# === Shutdown====
async def shutdown():
    print("[Shutdown] Chiusura in corso...")
    # 1. Stop worker & radio monitor
    if g.radio_monitor_task:
        g.radio_monitor_task.cancel()
    await g.send_queue.put(None)
    if g.worker_task:
        try:
            await asyncio.wait_for(g.worker_task, timeout=2)
        except asyncio.TimeoutError:
            print("[Shutdown] Worker timeout, forzo exit")
    # 2. Chiudi WebSocket
    for ws in g.ws_clients.copy():
        try:
            await ws.close()
        except:
            pass
    for hs in g.history_clients.copy():
        try:
            await hs.close()
        except:
            pass
    g.ws_clients.clear()
    g.history_clients.clear()
    # 3. Stop Uvicorn
    if g.ws_server:
        g.ws_server.should_exit = True
        try:
            await asyncio.wait_for(g.ws_server_task, timeout=2)
        except asyncio.TimeoutError:
            print("[Shutdown] UVicorn timeout, forzo exit")
    # 4. Chiudi seriale
    await serial.release_serial()
    # 5. Chiudi DB
    await db.engine.dispose()
    print("[Shutdown] Terminato")

# ===== Main =====
async def main():
    # Init DB
    await db.init_db()
    # Start WebSocket
    g.ws_server_task = asyncio.create_task(ws_endpoints.start_ws_server())
    # Avvio worker coda e monitor radio
    g.worker_task = asyncio.create_task(serial.queue_worker())
    g.radio_monitor_task = asyncio.create_task(serial.radio_monitor())
    # Connect MQTT
    g.mqtt_client = AsyncioPahoClient()
    g.mqtt_client.tls_set(ca_certs=c.MQTT_CA_CERTS)
    g.mqtt_client.tls_insecure_set(False)
    g.mqtt_client.username_pw_set(c.MQTT_USER, c.MQTT_PASS)
    g.mqtt_client.asyncio_listeners.add_on_connect(mqtt.on_connect)
    g.mqtt_client.asyncio_listeners.add_on_message(mqtt.on_message)
    await g.mqtt_client.asyncio_connect(c.MQTT_BROKER, port=c.MQTT_PORT, keepalive=60)
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError, Exception) as e:
        print(e)
    finally:
        # Stop server in modo pulito
        await shutdown()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Meshtray Server")
    parser.add_argument("--device-debug", action="store_true", help="Abilita il logging debug dello strato radio / firmware del dispositivo Meshtastic")
    args = parser.parse_args()

    g.device_debug = args.device_debug
    if g.device_debug:
        print("[INFO] Logging debug dello strato firmware Meshtastic abilitato su stdout.")

    asyncio.run(main())
