-- 001_init.sql: Core schema for TG Trails / OutLoot

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    display_name TEXT,
    status TEXT DEFAULT 'ACTIVE'
);

CREATE TABLE IF NOT EXISTS installations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    state TEXT NOT NULL DEFAULT 'IDLE',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    paused_reason TEXT,
    session_elapsed_s REAL DEFAULT 0.0,
    cycle_progress_s REAL DEFAULT 0.0,
    cycle_required_s REAL NOT NULL,
    distance_m REAL DEFAULT 0.0,
    cycle_start_lat REAL,
    cycle_start_lon REAL,
    invalid_reason TEXT,
    config_snapshot_json TEXT
);

CREATE TABLE IF NOT EXISTS movement_events (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    t REAL NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    accuracy_m REAL NOT NULL,
    verdict TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    seg_speed_mps REAL
);

CREATE TABLE IF NOT EXISTS item_definitions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'nature',
    rarity TEXT NOT NULL,
    base_points INTEGER NOT NULL,
    weight INTEGER NOT NULL DEFAULT 10,
    active BOOLEAN NOT NULL DEFAULT 1,
    description TEXT
);

CREATE TABLE IF NOT EXISTS spawned_items (
    id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL REFERENCES item_definitions(id),
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'LOCKED',
    spawned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    available_at TIMESTAMP,
    expires_at TIMESTAMP,
    collected_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS collections (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    spawn_id TEXT,
    user_id TEXT NOT NULL REFERENCES users(id),
    idempotency_key TEXT UNIQUE,
    result TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    points INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Partial unique index to guarantee a spawned item can only be successfully collected once
CREATE UNIQUE INDEX IF NOT EXISTS uq_spawn_success ON collections(spawn_id) WHERE result = 'SUCCESS';

CREATE TABLE IF NOT EXISTS point_transactions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    delta INTEGER NOT NULL,
    kind TEXT NOT NULL,
    ref_type TEXT,
    ref_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    note TEXT
);

CREATE TABLE IF NOT EXISTS sponsors (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT DEFAULT 'ACTIVE'
);

CREATE TABLE IF NOT EXISTS rewards (
    id TEXT PRIMARY KEY,
    sponsor_id TEXT REFERENCES sponsors(id),
    title TEXT NOT NULL,
    description TEXT,
    cost_points INTEGER NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0,
    state TEXT NOT NULL DEFAULT 'ACTIVE',
    valid_from TIMESTAMP,
    valid_to TIMESTAMP,
    terms TEXT
);

CREATE TABLE IF NOT EXISTS redemptions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    reward_id TEXT NOT NULL REFERENCES rewards(id),
    code TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'CONFIRMED',
    idempotency_key TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fulfilled_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS missions (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id),
    source TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    latency_ms REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    detail_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_point_tx_user ON point_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_spawned_items_session_status ON spawned_items(session_id, status);
CREATE INDEX IF NOT EXISTS idx_movement_events_session_t ON movement_events(session_id, t);
CREATE INDEX IF NOT EXISTS idx_sessions_user_state ON sessions(user_id, state);
