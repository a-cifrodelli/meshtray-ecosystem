import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
import mqtt_handler as mqtt

class MockMsg:
    def __init__(self, topic, payload):
        self.topic = topic
        self.payload = payload

@pytest.mark.asyncio
async def test_on_connect():
    client_mock = AsyncMock()
    await mqtt.on_connect(client_mock, None, None, 0)
    
    # Verifica le sottoscrizioni ai topic configurati
    client_mock.subscribe.assert_any_call("msh/#")
    client_mock.subscribe.assert_any_call("meshtastic/outgoing")

@pytest.mark.asyncio
async def test_on_message_ignored_channel():
    client_mock = MagicMock()
    # Canale "2" configurato come ignorato in config.py
    payload = json.dumps({"channel": "2", "from": "node_A", "to": "node_B", "payload": {"text": "hello"}})
    msg = MockMsg("msh/json/1", payload.encode("utf-8"))
    
    with patch("mqtt_handler.db.db_session_factory", None), \
         patch("mqtt_handler.ws.broadcast_ws", AsyncMock()) as ws_mock:
        await mqtt.on_message(client_mock, None, msg)
        ws_mock.assert_not_called()

@pytest.mark.asyncio
async def test_on_message_save_to_db_and_broadcast():
    client_mock = MagicMock()
    payload_data = {"channel": "1", "from": "node_A", "to": "node_B", "payload": {"text": "Hello MQTT!"}}
    msg = MockMsg("msh/json/1", json.dumps(payload_data).encode("utf-8"))
    
    # Mocking db_session_factory e la sessione asincrona
    session_mock = AsyncMock()
    entered_session = AsyncMock()
    entered_session.add = MagicMock()
    session_mock.__aenter__.return_value = entered_session
    
    session_factory_mock = MagicMock()
    session_factory_mock.return_value = session_mock
    
    with patch("mqtt_handler.db.db_session_factory", session_factory_mock), \
         patch("mqtt_handler.ws.broadcast_ws", AsyncMock()) as ws_mock, \
         patch("mqtt_handler.serial.send_to_mesh", AsyncMock()) as serial_mock:
        
        await mqtt.on_message(client_mock, None, msg)
        
        # Verifica salvataggio nel database
        session_factory_mock.assert_called_once()
        session_mock.__aenter__.assert_called_once()
        entered_session.add.assert_called_once()
        entered_session.commit.assert_called_once()
        
        # Verifica broadcast WebSocket
        ws_mock.assert_called_once_with(payload_data)

@pytest.mark.asyncio
async def test_on_message_outgoing():
    client_mock = MagicMock()
    payload_data = {"text": "Go to mesh"}
    msg = MockMsg("meshtastic/outgoing", json.dumps(payload_data).encode("utf-8"))
    
    with patch("mqtt_handler.db.db_session_factory", None), \
         patch("mqtt_handler.ws.broadcast_ws", AsyncMock()) as ws_mock, \
         patch("mqtt_handler.serial.send_to_mesh", AsyncMock()) as serial_mock:
        
        await mqtt.on_message(client_mock, None, msg)
        
        # Verifica inoltro a seriale
        serial_mock.assert_called_once_with(payload_data)
        # Verifica broadcast WebSocket
        ws_mock.assert_called_once_with(payload_data)
