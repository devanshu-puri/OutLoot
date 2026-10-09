from pathlib import Path
from typing import List, Literal, Optional
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseModel):
    name: str = "TG Trails"
    version: str = "0.1.0"
    demo_mode: bool = False


class MovementConfig(BaseModel):
    cycle_required_s: int = 300
    demo_cycle_required_s: int = 20
    min_displacement_m: float = 75.0
    max_gap_s: float = 30.0
    max_accuracy_m: float = 30.0
    min_walk_speed_mps: float = 0.5
    max_walk_speed_mps: float = 3.5
    impossible_speed_mps: float = 12.0
    noise_floor_m: float = 3.0
    max_skew_s: float = 60.0


class SpawnConfig(BaseModel):
    spawn_min_m: float = 80.0
    spawn_max_m: float = 250.0
    min_separation_m: float = 50.0
    collect_radius_m: float = 30.0
    retry_cooldown_s: float = 5.0


class LimitsConfig(BaseModel):
    max_collections_per_session: int = 12
    max_points_per_session: int = 600
    max_points_per_day: int = 1500
    max_session_duration_s: int = 10800
    raw_samples_keep_count: int = 200
    raw_samples_ttl_days: int = 7


class ItemDefConfig(BaseModel):
    id: str
    name: str
    category: str = "nature"
    rarity: Literal["common", "uncommon", "rare", "epic", "special"]
    base_points: int
    weight: int
    active: bool = True
    description: str = ""


class RewardDefConfig(BaseModel):
    id: str
    title: str
    description: str = ""
    cost_points: int
    stock: int = 10
    state: str = "ACTIVE"
    terms: str = "Demo reward"


class GameConfig(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    movement: MovementConfig = Field(default_factory=MovementConfig)
    spawn: SpawnConfig = Field(default_factory=SpawnConfig)
    limits: LimitsConfig = Field(default_factory=LimitsConfig)
    items: List[ItemDefConfig] = Field(default_factory=list)
    rewards: List[RewardDefConfig] = Field(default_factory=list)

    @property
    def active_cycle_required_s(self) -> int:
        if self.app.demo_mode:
            return self.movement.demo_cycle_required_s
        return self.movement.cycle_required_s


def load_game_config(config_path: Optional[Path] = None) -> GameConfig:
    if config_path is None:
        config_path = Path(__file__).resolve().parent.parent / "config" / "game.yaml"

    if not config_path.exists():
        return GameConfig()

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return GameConfig(**data)


class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    db_path: str = "data/tg_trails.db"
    admin_token: str = "dev_admin_secret_token_change_me"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma2:2b"
    ollama_timeout_s: float = 8.0

    rate_limit_per_minute: int = 60

    # Resolved game config
    game_config: GameConfig = Field(default_factory=load_game_config)


_settings_instance: Optional[ServerSettings] = None


def get_settings() -> ServerSettings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = ServerSettings()
        # Ensure game config is loaded from canonical file if default factory ran before path resolved
        _settings_instance.game_config = load_game_config()
    return _settings_instance
