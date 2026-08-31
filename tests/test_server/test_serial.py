import pytest
import asyncio
import json
from unittest.mock import MagicMock, patch, AsyncMock
import globals as g
import serial_handler as serial

@pytest.mark.asyncio
async def test_acquire_release_serial():
    mock_serial = MagicMock()
    with patch("meshtastic.serial_interface.SerialInterface", return_value=mock_serial) as mock_class:
        g.iface = None
        await serial.acquire_serial()
        assert g.iface == mock_serial
        mock_class.assert_called_once()
        
        await serial.release_serial()
        assert g.iface is None
        mock_serial.close.assert_called_once()

@pytest.mark.asyncio
async def test_send_to_mesh_success():
    # Svuota la coda prima di iniziare
    while not g.send_queue.empty():
        g.send_queue.get_nowait()
        
    payload = {"text": "Hello serial"}
    await serial.send_to_mesh(payload)
    
    assert g.send_queue.qsize() == 1
    queued = g.send_queue.get_nowait()
    assert queued == payload

@pytest.mark.asyncio
async def test_send_to_mesh_queue_full():
    # Forza una coda piena
    g.send_queue = asyncio.Queue(maxsize=1)
    g.send_queue.put_nowait({"text": "existing"})
    
    mqtt_client_mock = MagicMock()
    g.mqtt_client = mqtt_client_mock
    
    payload = {"text": "overflow"}
    await serial.send_to_mesh(payload)
    
    # Verifica che pubblichi sul topic di waiting
    mqtt_client_mock.publish.assert_called_once_with(
        "/meshtastic/waiting", 
        json.dumps(payload)
    )

@pytest.mark.asyncio
async def test_queue_worker_execution():
    g.send_queue = asyncio.Queue()
    payload = {"text": "Worker test message", "to": "node123", "channel_index": 1}
    g.send_queue.put_nowait(payload)
    # Accoda None per segnalare l'interruzione al worker
    g.send_queue.put_nowait(None)

    mock_iface = MagicMock()
    g.iface = mock_iface

    with patch("serial_handler.acquire_serial", AsyncMock()) as mock_acquire, \
         patch("globals.iface", mock_iface):

         await serial.queue_worker()

         # Verifica le chiamate per l'invio del messaggio sulla mesh
         mock_iface.sendText.assert_called_once_with(
             "Worker test message",
             destinationId="node123",
             channelIndex=1
         )
         mock_acquire.assert_called_once()
