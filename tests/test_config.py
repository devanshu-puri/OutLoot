import pytest
from pathlib import Path
from server.settings import load_game_config, GameConfig, ServerSettings


def test_game_config_loads_defaults():
    config = load_game_config()
    assert config.app.name == "TG Trails"
    assert config.movement.min_walk_speed_mps == 0.5
    assert config.movement.max_walk_speed_mps == 3.5
    assert config.spawn.collect_radius_m == 30.0
    assert len(config.items) >= 4
    assert len(config.rewards) >= 3


def test_demo_mode_cycle_switch():
    config = load_game_config()
    config.app.demo_mode = False
    assert config.active_cycle_required_s == config.movement.cycle_required_s
    config.app.demo_mode = True
    assert config.active_cycle_required_s == config.movement.demo_cycle_required_s


def test_server_settings_instance():
    settings = ServerSettings()
    assert settings.port == 8000
    assert settings.ollama_base_url.startswith("http")
    assert settings.game_config.app.name == "TG Trails"
