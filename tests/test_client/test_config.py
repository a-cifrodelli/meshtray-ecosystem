import os
import sys
import importlib
import pytest
import dotenv

@pytest.fixture(autouse=True)
def mock_dotenv(monkeypatch):
    # Impedisce a dotenv di caricare il file .env reale su disco durante i test di configurazione
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr(dotenv, "find_dotenv", lambda *args, **kwargs: "")

def test_ws_url_derivation_default(monkeypatch):
    # Rimuove le variabili d'ambiente per forzare i default
    monkeypatch.delenv("WS_BASE_URL", raising=False)
    monkeypatch.delenv("WS_URL_NOTIFICATION", raising=False)
    monkeypatch.delenv("WS_URL_HISTORY", raising=False)
    monkeypatch.delenv("WS_URL_SEND", raising=False)
    monkeypatch.delenv("WS_URL_NODES", raising=False)

    import config
    importlib.reload(config)

    assert config.WS_BASE_URL == "ws://localhost:8088"
    assert config.WS_URL_NOTIFICATION == "ws://localhost:8088/ws/notifications"
    assert config.WS_URL_HISTORY == "ws://localhost:8088/ws/history"
    assert config.WS_URL_SEND == "ws://localhost:8088/ws/send"
    assert config.WS_URL_NODES == "ws://localhost:8088/ws/nodes_channels"

def test_ws_url_derivation_custom_base(monkeypatch):
    # Imposta un WS_BASE_URL personalizzato sicuro con slash finale
    monkeypatch.setenv("WS_BASE_URL", "wss://192.168.1.100:9099/")
    monkeypatch.delenv("WS_URL_NOTIFICATION", raising=False)
    monkeypatch.delenv("WS_URL_HISTORY", raising=False)
    monkeypatch.delenv("WS_URL_SEND", raising=False)
    monkeypatch.delenv("WS_URL_NODES", raising=False)

    import config
    importlib.reload(config)

    assert config.WS_BASE_URL == "wss://192.168.1.100:9099"
    assert config.WS_URL_NOTIFICATION == "wss://192.168.1.100:9099/ws/notifications"
    assert config.WS_URL_HISTORY == "wss://192.168.1.100:9099/ws/history"
    assert config.WS_URL_SEND == "wss://192.168.1.100:9099/ws/send"
    assert config.WS_URL_NODES == "wss://192.168.1.100:9099/ws/nodes_channels"

def test_ws_url_derivation_overrides(monkeypatch):
    # Imposta un WS_BASE_URL ma sovrascrive esplicitamente un endpoint per retrocompatibilità
    monkeypatch.setenv("WS_BASE_URL", "ws://localhost:8088")
    monkeypatch.setenv("WS_URL_NOTIFICATION", "wss://secure-server/ws/custom_notif")
    monkeypatch.delenv("WS_URL_HISTORY", raising=False)
    monkeypatch.delenv("WS_URL_SEND", raising=False)
    monkeypatch.delenv("WS_URL_NODES", raising=False)

    import config
    importlib.reload(config)

    assert config.WS_URL_NOTIFICATION == "wss://secure-server/ws/custom_notif"
    assert config.WS_URL_HISTORY == "ws://localhost:8088/ws/history"
    assert config.WS_URL_SEND == "ws://localhost:8088/ws/send"
    assert config.WS_URL_NODES == "ws://localhost:8088/ws/nodes_channels"
