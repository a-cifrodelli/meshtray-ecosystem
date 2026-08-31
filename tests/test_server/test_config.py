import os
import config

def test_config_paths():
    assert os.path.exists(config.BASE_DIR)
    assert os.path.exists(config.PROJECT_DIR)

def test_config_defaults():
    assert config.MQTT_PORT == 8883
    assert config.WS_PORT == 8088
    assert config.WS_HOST == "0.0.0.0"
    assert config.QUEUE_MAXSIZE == 50
    assert "memory" in config.DATABASE_URL
