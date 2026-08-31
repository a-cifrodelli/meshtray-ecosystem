import pytest
import os
from connection import ConnectionThread

def test_connection_thread_initialization():
    thread = ConnectionThread(is_mock=True, mock_delay=1.0)
    assert thread.is_mock is True
    assert thread.mock_delay == 1.0
    assert thread.loop is None
    assert thread.stop_event is None

def test_connection_get_ssl_context(monkeypatch):
    # Test della logica _get_ssl_context
    thread = ConnectionThread()
    
    # 1. ws:// non deve mai avere SSLContext
    ctx_ws = thread._get_ssl_context("ws://localhost:8088/ws/notifications")
    assert ctx_ws is None

    # 2. wss:// senza ROOT_CA non deve avere SSLContext (usa il default di sistema o None)
    monkeypatch.setattr("connection.ROOT_CA", "")
    ctx_wss_no_ca = thread._get_ssl_context("wss://localhost:8088/ws/notifications")
    assert ctx_wss_no_ca is None

    # 3. wss:// con ROOT_CA che non esiste non deve avere SSLContext
    monkeypatch.setattr("connection.ROOT_CA", "percorso_inesistente_ca.pem")
    ctx_wss_bad_ca = thread._get_ssl_context("wss://localhost:8088/ws/notifications")
    assert ctx_wss_bad_ca is None
