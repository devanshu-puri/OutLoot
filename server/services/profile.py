import datetime
import hashlib
import secrets
import sqlite3
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from server.db import tx
from server.schemas import DailyStatItem, ProfileResponse, ProfileUpdateReq
from server.services.points import get_points_balance


def get_today_str() -> str:
    return datetime.date.today().isoformat()


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return hashed, salt


def verify_password(password: str, stored_hash_with_salt: str) -> bool:
    if ":" not in stored_hash_with_salt:
        return False
    salt, hashed = stored_hash_with_salt.split(":", 1)
    check_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(check_hash, hashed)


def record_daily_stats(
    conn: sqlite3.Connection,
    user_id: str,
    delta_screen_s: float = 0.0,
    delta_distance_m: float = 0.0,
    delta_points: int = 0,
    delta_items: int = 0,
    delta_walk_s: float = 0.0,
    stat_date: Optional[str] = None
) -> None:
    if not stat_date:
        stat_date = get_today_str()

    stat_id = f"dus_{user_id}_{stat_date}"
    with tx(conn):
        conn.execute(
            """
            INSERT INTO daily_user_stats (id, user_id, stat_date, screen_time_s, distance_m, points_collected, items_collected, walk_time_s, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, stat_date) DO UPDATE SET
                screen_time_s = screen_time_s + excluded.screen_time_s,
                distance_m = distance_m + excluded.distance_m,
                points_collected = points_collected + excluded.points_collected,
                items_collected = items_collected + excluded.items_collected,
                walk_time_s = walk_time_s + excluded.walk_time_s,
                updated_at = CURRENT_TIMESTAMP;
            """,
            (stat_id, user_id, stat_date, delta_screen_s, delta_distance_m, delta_points, delta_items, delta_walk_s)
        )


def get_user_profile(conn: sqlite3.Connection, user_id: str) -> ProfileResponse:
    user = conn.execute("SELECT * FROM users WHERE id = ?;", (user_id,)).fetchone()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "USER_NOT_FOUND", "message": "User not found"}
        )

    pts = get_points_balance(conn, user_id)
    out_s = float(user["outdoor_time_total_s"] or 0.0)
    screen_s = float(user["screen_time_total_s"] or 0.0)
    total_s = out_s + screen_s
    ratio = round(out_s / total_s, 3) if total_s > 0 else 0.0

    today = get_today_str()
    today_row = conn.execute(
        "SELECT * FROM daily_user_stats WHERE user_id = ? AND stat_date = ?;",
        (user_id, today)
    ).fetchone()

    if today_row:
        today_stat = DailyStatItem(
            stat_date=today,
            screen_time_mins=round(float(today_row["screen_time_s"]) / 60.0, 1),
            distance_m=round(float(today_row["distance_m"]), 1),
            points_collected=int(today_row["points_collected"]),
            items_collected=int(today_row["items_collected"]),
            walk_time_mins=round(float(today_row["walk_time_s"]) / 60.0, 1)
        )
    else:
        today_stat = DailyStatItem(
            stat_date=today,
            screen_time_mins=round(screen_s / 60.0, 1),
            distance_m=0.0,
            points_collected=0,
            items_collected=0,
            walk_time_mins=round(out_s / 60.0, 1)
        )

    # Fetch last 7 days
    recent_rows = conn.execute(
        """
        SELECT * FROM daily_user_stats
        WHERE user_id = ?
        ORDER BY stat_date DESC
        LIMIT 7;
        """,
        (user_id,)
    ).fetchall()

    recent_daily: List[DailyStatItem] = []
    for r in recent_rows:
        recent_daily.append(DailyStatItem(
            stat_date=r["stat_date"],
            screen_time_mins=round(float(r["screen_time_s"]) / 60.0, 1),
            distance_m=round(float(r["distance_m"]), 1),
            points_collected=int(r["points_collected"]),
            items_collected=int(r["items_collected"]),
            walk_time_mins=round(float(r["walk_time_s"]) / 60.0, 1)
        ))

    # Calculate user rank based on grass score
    my_score = pts + int(out_s / 60.0 * 2)
    higher_count = conn.execute(
        """
        SELECT COUNT(*) FROM users
        WHERE status = 'ACTIVE' AND id != ? AND (outdoor_time_total_s / 30.0 + ?) < (outdoor_time_total_s / 30.0);
        """,
        (user_id, pts)
    ).fetchone()[0]
    rank = max(1, higher_count + 1)

    return ProfileResponse(
        user_id=user_id,
        username=user["username"] if "username" in user.keys() else None,
        display_name=str(user["display_name"] or "Trail Explorer"),
        avatar_emoji=str(user["avatar_emoji"] if "avatar_emoji" in user.keys() and user["avatar_emoji"] else "🌱"),
        bio=str(user["bio"] if "bio" in user.keys() and user["bio"] else "Outdoor trail explorer"),
        status_msg=str(user["status_msg"] if "status_msg" in user.keys() and user["status_msg"] else "Ready to touch grass"),
        total_points=pts,
        outdoor_mins=round(out_s / 60.0, 1),
        screen_mins=round(screen_s / 60.0, 1),
        touch_grass_ratio=ratio,
        rank=rank,
        today_stats=today_stat,
        recent_daily=recent_daily
    )


def update_user_profile(
    conn: sqlite3.Connection,
    user_id: str,
    req: ProfileUpdateReq
) -> ProfileResponse:
    with tx(conn):
        user = conn.execute("SELECT * FROM users WHERE id = ?;", (user_id,)).fetchone()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        updates = []
        params = []
        if req.display_name is not None and req.display_name.strip():
            updates.append("display_name = ?")
            params.append(req.display_name.strip())
        if req.avatar_emoji is not None and req.avatar_emoji.strip():
            updates.append("avatar_emoji = ?")
            params.append(req.avatar_emoji.strip())
        if req.bio is not None:
            updates.append("bio = ?")
            params.append(req.bio.strip())
        if req.status_msg is not None:
            updates.append("status_msg = ?")
            params.append(req.status_msg.strip())

        if updates:
            params.append(user_id)
            conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?;", tuple(params))

    return get_user_profile(conn, user_id)
