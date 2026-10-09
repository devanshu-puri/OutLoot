-- 002_social_and_screentime.sql: Real-time screen time tracking, friends system & leaderboard

ALTER TABLE users ADD COLUMN screen_time_total_s REAL DEFAULT 0.0;
ALTER TABLE users ADD COLUMN outdoor_time_total_s REAL DEFAULT 0.0;
ALTER TABLE users ADD COLUMN screen_time_threshold_s REAL DEFAULT 1800.0; -- default 30 mins (1800s)
ALTER TABLE users ADD COLUMN current_screen_streak_s REAL DEFAULT 0.0;
ALTER TABLE users ADD COLUMN avatar_emoji TEXT DEFAULT '🌱';
ALTER TABLE users ADD COLUMN last_seen_at TIMESTAMP DEFAULT NULL;
ALTER TABLE users ADD COLUMN status_msg TEXT DEFAULT 'Ready to touch grass';

CREATE TABLE IF NOT EXISTS friends (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    friend_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'ACCEPTED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, friend_id)
);

CREATE TABLE IF NOT EXISTS friend_nudges (
    id TEXT PRIMARY KEY,
    sender_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    receiver_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    seen BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS screen_time_events (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    active_s REAL NOT NULL,
    idle_s REAL NOT NULL DEFAULT 0.0,
    source TEXT DEFAULT 'web_active',
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_friends_user ON friends(user_id);
CREATE INDEX IF NOT EXISTS idx_friends_friend ON friends(friend_id);
CREATE INDEX IF NOT EXISTS idx_friend_nudges_receiver ON friend_nudges(receiver_id, seen);
CREATE INDEX IF NOT EXISTS idx_screen_time_user_time ON screen_time_events(user_id, recorded_at);
