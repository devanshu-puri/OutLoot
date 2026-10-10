-- 003_profile_auth_and_daily.sql: User Auth, Profile credentials & Daily Activity Stats

ALTER TABLE users ADD COLUMN username TEXT;
ALTER TABLE users ADD COLUMN password_hash TEXT;
ALTER TABLE users ADD COLUMN bio TEXT DEFAULT 'Outdoor trail explorer';

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username) WHERE username IS NOT NULL;

CREATE TABLE IF NOT EXISTS daily_user_stats (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stat_date TEXT NOT NULL,
    screen_time_s REAL DEFAULT 0.0,
    distance_m REAL DEFAULT 0.0,
    points_collected INTEGER DEFAULT 0,
    items_collected INTEGER DEFAULT 0,
    walk_time_s REAL DEFAULT 0.0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, stat_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_user_date ON daily_user_stats(user_id, stat_date);
