import asyncio
import json
import datetime
from sqlalchemy import select, or_, and_
from models import Message
from fastapi import WebSocket, WebSocketDisconnect
import uvicorn
import config as c
import globals as g
import db_engine as db
import serial_handler as serial

# ===== WebSocket =====
@g.ws_app.websocket("/ws/notifications")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    g.ws_clients.add(ws)
    try:
        await ws.receive()
    except (asyncio.exceptions.CancelledError, WebSocketDisconnect) as e:
        print(e)
    finally:
        g.ws_clients.discard(ws)

@g.ws_app.websocket("/ws/history")
async def websocket_history(ws: WebSocket):
    await ws.accept()
    g.history_clients.add(ws)
    try:
        while True:
            data = await ws.receive_text()
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                await ws.send_text(json.dumps({"error": "Invalid JSON"}))
                continue

            action = payload.get("action")
            if action == "get":
                offset = int(payload.get("offset", 0))
                limit = int(payload.get("limit", 50))
                filter_target = payload.get("filter_target")
                filter_channel = payload.get("filter_channel")

                query = select(Message)
                if filter_target:
                    # DM filter: either sender is target and not broadcast, or we sent to target
                    query = query.where(
                        or_(
                            and_(Message.sender == filter_target, Message.dest != "^all"),
                            and_(Message.sender == "local_node", Message.dest == filter_target)
                        )
                    )
                elif filter_channel:
                    # Channel filter
                    query = query.where(Message.channel == filter_channel)

                async with db.db_session_factory() as session:
                    result = await session.execute(
                        query.order_by(Message.timestamp.desc())
                        .offset(offset)
                        .limit(limit)
                    )
                    rows = result.scalars().all()

                messages = [
                    {
                        "id": m.id,
                        "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                        "sender": m.sender,
                        "dest": m.dest,
                        "text": m.text,
                        "channel": m.channel,
                        "seen": m.seen,
                    }
                    for m in rows
                ]

                await ws.send_text(json.dumps({"messages": messages}))
            else:
                await ws.send_text(json.dumps({"error": "Unknown action"}))
    except WebSocketDisconnect as e:
        print(e) # chiusura normale
    except Exception as e:
        # Questa cattura anche chiusure come AbnormalClosure
        print(f"[History WS error] {e}")
    finally:
        g.history_clients.discard(ws)
        print("[History WS] Connection closed")

@g.ws_app.websocket("/ws/send")
async def websocket_send(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            data = await ws.receive_text()
            try:
                payload = json.loads(data)
                text = payload.get("text", "")
                to_node = payload.get("to", "")
                channel = payload.get("channel", "default")
                
                # Setup out payload for queue worker
                # If 'to' is specified, it's a DM, so channel index should be 0.
                channel_index = 0
                if not to_node:
                    # In real Meshtastic, channel names are mapped to indexes, but default to 0
                    channel_index = 0
                
                mesh_payload = {
                    "text": text,
                    "to": to_node if to_node else None,
                    "channel_index": channel_index
                }
                
                # Send to serial queue worker
                await serial.send_to_mesh(mesh_payload)
                
                # Save outgoing message to DB
                if db.db_session_factory:
                    async with db.db_session_factory() as session:
                        msg_obj = Message(
                            sender="local_node",
                            dest=to_node if to_node else "^all",
                            text=text,
                            channel="DM" if to_node else channel,
                            seen=True
                        )
                        session.add(msg_obj)
                        await session.commit()
                        
                        # Broadcast to all live WS notification clients (so they update MainWindow)
                        broadcast_payload = {
                            "channel": msg_obj.channel,
                            "from": msg_obj.sender,
                            "to": msg_obj.dest,
                            "text": msg_obj.text,
                            "payload": {"text": msg_obj.text},
                            "timestamp": int(datetime.datetime.now(datetime.timezone.utc).timestamp())
                        }
                        await broadcast_ws(broadcast_payload)
                
                await ws.send_text(json.dumps({"status": "success"}))
            except json.JSONDecodeError:
                await ws.send_text(json.dumps({"status": "error", "message": "Invalid JSON"}))
            except Exception as e:
                await ws.send_text(json.dumps({"status": "error", "message": str(e)}))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS Send Error] {e}")

@g.ws_app.websocket("/ws/nodes_channels")
async def websocket_nodes_channels(ws: WebSocket):
    await ws.accept()
    try:
        nodes, channels, radio_online = await serial.get_radio_nodes_channels()
            
        await ws.send_text(json.dumps({
            "nodes": nodes,
            "channels": channels,
            "radio_online": radio_online
        }))
    except Exception as e:
        print(f"[WS Nodes/Channels Error] {e}")
    finally:
        try:
            await ws.close()
        except:
            pass

async def broadcast_ws(payload: dict):
    msg_text = json.dumps(payload)
    for ws in g.ws_clients.copy():
        try:
            await asyncio.wait_for(ws.send_text(msg_text), timeout=1)
        except Exception:
            g.ws_clients.discard(ws)

async def start_ws_server():
    config = uvicorn.Config(g.ws_app, host=c.WS_HOST, port=c.WS_PORT, log_level="info", lifespan="off", timeout_graceful_shutdown=5)
    g.ws_server = uvicorn.Server(config)
    g.ws_server_task = asyncio.create_task(g.ws_server.serve())
    return g.ws_server_task
