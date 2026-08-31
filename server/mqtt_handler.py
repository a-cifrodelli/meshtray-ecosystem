import json
from models import Message # ORM già definito altrove
import config as c
import websocket_endpoints as ws
import serial_handler as serial
import db_engine as db

# ===== MQTT Handlers =====
async def on_connect(client, userdata, flags, rc, properties=None):
    print("[MQTT] Connesso con codice", rc)
    await client.subscribe(c.MQTT_TOPIC_IN)
    await client.subscribe(c.MQTT_TOPIC_OUT)

async def on_message(client, userdata, msg):
    topic = msg.topic
    try:
        payload = json.loads(msg.payload.decode('utf-8', errors='ignore'))
    except json.JSONDecodeError:
        if "/json/" in topic:
            print(f"[MQTT] payload non valido: {topic} {msg.payload}")
        return

    channel = payload.get("channel", "default")
    if str(channel) in c.IGNORED_CHANNELS:
        return

    # Salvataggio su DB asincrono
    if "/json/" in topic and db.db_session_factory:
        p = payload.get("payload", "")
        text = p.get("text", "")
        if text:
            async with db.db_session_factory() as session:
                msg_obj = Message(
                    sender=payload.get("from", "unknown"),
                    dest=payload.get("to", ""),
                    text=text,
                    channel=channel,
                    seen=False
                )
                session.add(msg_obj)
                await session.commit()

    if topic.endswith(c.MQTT_TOPIC_OUT):
        await serial.send_to_mesh(payload)

    await ws.broadcast_ws(payload)
