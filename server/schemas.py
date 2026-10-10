from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    retry_after_s: Optional[float] = None


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    db_ok: bool
    ollama_reachable: bool
    ollama_model: str
    active_connections: int = 0


class AnonAuthResponse(BaseModel):
    user_id: str
    token: str
    display_name: str


class SessionStartReq(BaseModel):
    display_name: Optional[str] = "Trail Walker"
    start_lat: Optional[float] = None
    start_lon: Optional[float] = None


class SpawnedItemHint(BaseModel):
    id: str
    rarity: str
    base_points: int
    name: str
    category: str
    status: Literal["LOCKED", "AVAILABLE", "COLLECTED", "EXPIRED"]
    lat: Optional[float] = None
    lon: Optional[float] = None
    distance_m: Optional[float] = None
    bearing_deg: Optional[float] = None


class SessionResponse(BaseModel):
    id: str
    user_id: str
    state: str
    started_at: str
    ended_at: Optional[str] = None
    paused_reason: Optional[str] = None
    session_elapsed_s: float
    cycle_progress_s: float
    cycle_required_s: float
    distance_m: float
    points_earned: int = 0
    collections_count: int = 0
    next_item: Optional[SpawnedItemHint] = None
    nearby_items: List[SpawnedItemHint] = Field(default_factory=list)
    invalid_reason: Optional[str] = None


class SampleItem(BaseModel):
    t: float = Field(description="Client timestamp in epoch seconds")
    lat: float
    lon: float
    accuracy_m: float
    speed_mps: Optional[float] = None
    step_count: Optional[int] = None


class SampleBatchReq(BaseModel):
    samples: List[SampleItem]


class RejectedSampleDetail(BaseModel):
    index: int
    reason_code: str
    detail: Optional[str] = None


class SampleBatchResp(BaseModel):
    accepted_count: int
    rejected: List[RejectedSampleDetail] = Field(default_factory=list)
    session_state: str
    cycle_progress_s: float
    cycle_required_s: float
    distance_m: float
    item_available: bool
    next_item: Optional[SpawnedItemHint] = None
    nearby_items: List[SpawnedItemHint] = Field(default_factory=list)


class CollectReq(BaseModel):
    spawn_id: str
    lat: float
    lon: float
    accuracy_m: float
    idempotency_key: str


class CollectResp(BaseModel):
    result: Literal["SUCCESS", "REPLAY", "REJECTED"]
    reason_code: str
    points_awarded: int
    new_balance: int
    cycle_progress_s: float
    message: str
    item_name: Optional[str] = None
    rarity: Optional[str] = None


class PointTxItem(BaseModel):
    id: str
    delta: int
    kind: str
    created_at: str
    note: Optional[str] = None


class BalanceResponse(BaseModel):
    balance: int
    recent_transactions: List[PointTxItem] = Field(default_factory=list)


class RewardItem(BaseModel):
    id: str
    title: str
    description: str
    cost_points: int
    stock: int
    state: str
    terms: str


class RedeemReq(BaseModel):
    idempotency_key: str


class RedemptionResp(BaseModel):
    id: str
    reward_id: str
    reward_title: str
    code: str
    status: str
    cost_points: int
    new_balance: int
    created_at: str
    replayed: bool = False


class MissionReq(BaseModel):
    minutes: int = Field(default=20, ge=5, le=60)
    interest: Optional[str] = "nature"
    intensity: Literal["easy", "moderate"] = "easy"
    environment: Optional[str] = "park trail"


class MissionPayload(BaseModel):
    title: str = Field(min_length=5, max_length=60)
    description: str = Field(min_length=20, max_length=280)
    est_minutes: int = Field(ge=5, le=60)
    intensity: Literal["easy", "moderate"]
    tip: str = Field(max_length=120)
    item_lore: str = Field(min_length=20, max_length=200)


class MissionResp(BaseModel):
    id: str
    source: Literal["gemma-local", "fallback"]
    payload: MissionPayload
    latency_ms: float
    created_at: str


class AdjustPointsReq(BaseModel):
    user_id: str
    delta: int
    note: str


# --- Screen Time & Digital Wellbeing ---

class ScreenTimeHeartbeatReq(BaseModel):
    active_s: float = Field(ge=0, description="Active engaged seconds since last heartbeat")
    idle_s: float = Field(default=0.0, ge=0, description="Idle/inactive seconds")


class ScreenTimeHeartbeatResp(BaseModel):
    screen_time_total_s: float
    current_screen_streak_s: float
    screen_time_threshold_s: float
    outdoor_time_total_s: float
    touch_grass_alert: bool
    touch_grass_ratio: float
    grass_debt_minutes: float
    message: str


class ScreenTimeImportReq(BaseModel):
    daily_screen_hours: float = Field(ge=0.1, le=24.0)
    device_label: str = "Android Digital Wellbeing"


class ScreenTimeImportResp(BaseModel):
    imported_hours: float
    total_screen_hours: float
    grass_debt_minutes: float
    suggested_walk_mins: int
    message: str


class UpdateThresholdReq(BaseModel):
    threshold_minutes: int = Field(ge=1, le=360)


# --- Friends & Social System ---

class AddFriendReq(BaseModel):
    friend_code_or_name: str


class FriendNudgeReq(BaseModel):
    friend_id: str
    message: Optional[str] = "🌱 Time to Touch Grass! Take a quick 15-min walk outside."


class FriendItem(BaseModel):
    user_id: str
    display_name: str
    avatar_emoji: str
    outdoor_mins: float
    screen_mins: float
    touch_grass_ratio: float
    points: int
    status_msg: str
    is_online: bool
    last_seen: str


class FriendNudgeItem(BaseModel):
    id: str
    sender_id: str
    sender_name: str
    sender_avatar: str
    message: str
    created_at: str


# --- Live Leaderboard ---

class LeaderboardItem(BaseModel):
    rank: int
    user_id: str
    display_name: str
    avatar_emoji: str
    grass_score: int
    points: int
    outdoor_mins: float
    screen_mins: float
    ratio_percent: int
    is_friend: bool
    is_current_user: bool


class LeaderboardResp(BaseModel):
    leaderboard: List[LeaderboardItem]
    user_rank: int
    total_walkers: int
    time_window: str = "Live All-Time"


# --- Profile & Account Management ---

class RegisterReq(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=4, max_length=60)
    display_name: Optional[str] = None


class LoginReq(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    user_id: str
    token: str
    username: Optional[str] = None
    display_name: str
    avatar_emoji: str = "🌱"
    bio: Optional[str] = None
    points: int = 0


class ProfileUpdateReq(BaseModel):
    display_name: Optional[str] = None
    avatar_emoji: Optional[str] = None
    bio: Optional[str] = None
    status_msg: Optional[str] = None


class DailyStatItem(BaseModel):
    stat_date: str
    screen_time_mins: float
    distance_m: float
    points_collected: int
    items_collected: int
    walk_time_mins: float


class ProfileResponse(BaseModel):
    user_id: str
    username: Optional[str] = None
    display_name: str
    avatar_emoji: str
    bio: Optional[str] = None
    status_msg: Optional[str] = None
    total_points: int
    outdoor_mins: float
    screen_mins: float
    touch_grass_ratio: float
    rank: int
    today_stats: DailyStatItem
    recent_daily: List[DailyStatItem] = Field(default_factory=list)

