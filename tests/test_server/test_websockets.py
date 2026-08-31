import asyncio
import pytest
from fastapi.testclient import TestClient
import globals as g
import db_engine as db
import websocket_endpoints as ws_endpoints
from models import Message

@pytest.mark.asyncio
async def test_websocket_notifications():
    client = TestClient(g.ws_app)
    with client.websocket_connect("/ws/notifications") as websocket:
        # Verifica che la connessione sia registrata in ws_clients
        assert len(g.ws_clients) == 1
        
        # Esegui il broadcast
        await ws_endpoints.broadcast_ws({"live": "update"})
        
        # Ricevi e convalida il messaggio trasmesso
        data = websocket.receive_json()
        assert data == {"live": "update"}
    
    # Verifica che il client sia rimosso alla disconnessione
    assert len(g.ws_clients) == 0

@pytest.mark.asyncio
async def test_websocket_history():
    # Inizializza il database in memoria e inserisce messaggi
    await db.init_db()
    
    async with db.db_session_factory() as session:
        # Pulisce la tabella dei messaggi
        from sqlalchemy import delete
        await session.execute(delete(Message))
        
        # Inserisce un messaggio di prova
        msg = Message(
            sender="ws_sender",
            dest="ws_dest",
            text="WebSocket history verification",
            channel="default",
            seen=False
        )
        session.add(msg)
        await session.commit()
        
    client = TestClient(g.ws_app)
    with client.websocket_connect("/ws/history") as websocket:
        # Richiede lo storico dei messaggi
        websocket.send_json({"action": "get", "offset": 0, "limit": 10})
        
        # Controlla la risposta del server
        response = websocket.receive_json()
        assert "messages" in response
        messages = response["messages"]
        assert len(messages) == 1
        assert messages[0]["sender"] == "ws_sender"
        assert messages[0]["text"] == "WebSocket history verification"

@pytest.mark.asyncio
async def test_websocket_history_filtered():
    await db.init_db()
    async with db.db_session_factory() as session:
        from sqlalchemy import delete
        await session.execute(delete(Message))
        
        # Insert target node messages and other messages
        msg1 = Message(sender="!target1", dest="local_node", text="private from target", channel="DM")
        msg2 = Message(sender="local_node", dest="!target1", text="private to target", channel="DM")
        msg3 = Message(sender="!other", dest="local_node", text="unrelated private", channel="DM")
        msg4 = Message(sender="!other", dest="^all", text="channel broadcast", channel="LongFast")
        
        session.add_all([msg1, msg2, msg3, msg4])
        await session.commit()

    client = TestClient(g.ws_app)
    with client.websocket_connect("/ws/history") as websocket:
        # Test 1: target node filter
        websocket.send_json({"action": "get", "offset": 0, "limit": 10, "filter_target": "!target1"})
        resp = websocket.receive_json()
        msgs = resp["messages"]
        assert len(msgs) == 2
        texts = [m["text"] for m in msgs]
        assert "private from target" in texts
        assert "private to target" in texts

        # Test 2: channel filter
        websocket.send_json({"action": "get", "offset": 0, "limit": 10, "filter_channel": "LongFast"})
        resp = websocket.receive_json()
        msgs = resp["messages"]
        assert len(msgs) == 1
        assert msgs[0]["text"] == "channel broadcast"

@pytest.mark.asyncio
async def test_websocket_send():
    from unittest.mock import AsyncMock, patch
    await db.init_db()
    
    # Mock serial.send_to_mesh
    mock_send = AsyncMock()
    with patch("serial_handler.send_to_mesh", mock_send):
        client = TestClient(g.ws_app)
        with client.websocket_connect("/ws/send") as websocket:
            websocket.send_json({
                "text": "Hello mesh from ws",
                "to": "!destnode",
                "channel": "default"
            })
            resp = websocket.receive_json()
            assert resp["status"] == "success"
            
            # Verify message is queued
            mock_send.assert_called_once()
            args = mock_send.call_args[0][0]
            assert args["text"] == "Hello mesh from ws"
            assert args["to"] == "!destnode"
            assert args["channel_index"] == 0

            # Verify saved to DB
            async with db.db_session_factory() as session:
                from sqlalchemy import select
                res = await session.execute(
                    select(Message).where(Message.text == "Hello mesh from ws")
                )
                msg = res.scalars().first()
                assert msg is not None
                assert msg.sender == "local_node"
                assert msg.dest == "!destnode"
                assert msg.channel == "DM"

@pytest.mark.asyncio
async def test_websocket_nodes_channels(monkeypatch):
    import serial_handler
    async def mock_get():
        return ["!node1", "!node2"], ["CustomChan"], True
    monkeypatch.setattr(serial_handler, "get_radio_nodes_channels", mock_get)

    client = TestClient(g.ws_app)
    with client.websocket_connect("/ws/nodes_channels") as websocket:
        resp = websocket.receive_json()
        assert "nodes" in resp
        assert "channels" in resp
        assert "radio_online" in resp
        assert resp["radio_online"] is True
        
        nodes = resp["nodes"]
        channels = resp["channels"]
        
        assert "!node1" in nodes
        assert "!node2" in nodes
        assert "CustomChan" in channels
        assert "DM" not in channels # DM is filtered out
