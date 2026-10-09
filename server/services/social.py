import secrets
import sqlite3
import time
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from server.db import tx
from server.schemas import (
    FriendItem,
    FriendNudgeItem,
    LeaderboardItem,
    LeaderboardResp,
    ScreenTimeHeartbeatResp,
    ScreenTimeImportResp,
)
from server.services.points import get_points_balance


def seed_demo_social_walkers_if_empty(conn: sqlite3.Connection, current_user_id: str) -> None:
    alex = conn.execute("SELECT id FROM users WHERE id = 'usr_alex_trail';").fetchone()
    if not alex:
        demo_walkers = [
            ("usr_alex_trail", "Alex Green", "🌲", 4200.0, 1800.0, 1800.0, 0.0, "Morning trail runner"),
            ("usr_maya_walker", "Maya Stride", "🏃‍♀️", 7800.0, 2400.0, 2700.0, 0.0, "Birdwatching & pacing"),
            ("usr_chen_flora", "Chen Scout", "🌿", 3100.0, 3600.0, 1800.0, 900.0, "Exploring city canopy"),
            ("usr_sara_quest", "Sara Woods", "🎒", 9500.0, 1200.0, 3600.0, 0.0, "Weekend hiker"),
            ("usr_kai_dev", "Kai Hacker", "💻", 1200.0, 9600.0, 1800.0, 3600.0, "Coding all day... need grass!")
        ]

        for uid, name, emoji, out_s, screen_s, thresh_s, streak_s, status_msg in demo_walkers:
            conn.execute(
                """
                INSERT OR IGNORE INTO users (id, display_name, status, outdoor_time_total_s, screen_time_total_s, screen_time_threshold_s, current_screen_streak_s, avatar_emoji, status_msg)
                VALUES (?, ?, 'ACTIVE', ?, ?, ?, ?, ?, ?);
                """,
                (uid, name, out_s, screen_s, thresh_s, streak_s, emoji, status_msg)
            )
            # Give points
            base_pts = int(out_s / 60.0 * 3.5)
            conn.execute(
                """
                INSERT OR IGNORE INTO point_transactions (id, user_id, delta, kind, created_at, note)
                VALUES (?, ?, ?, 'OUTDOOR_WALK', CURRENT_TIMESTAMP, 'Paced walk drops');
                """,
                (f"ptx_{secrets.token_hex(6)}", uid, base_pts)
            )
            # Add Alex Green as an automatic mutual friend
            if uid == "usr_alex_trail" and current_user_id:
                conn.execute(
                    "INSERT OR IGNORE INTO friends (id, user_id, friend_id, status) VALUES (?, ?, ?, 'ACCEPTED');",
                    (f"fr_{secrets.token_hex(6)}", current_user_id, uid)
                )
                conn.execute(
                    "INSERT OR IGNORE INTO friends (id, user_id, friend_id, status) VALUES (?, ?, ?, 'ACCEPTED');",
                    (f"fr_{secrets.token_hex(6)}", uid, current_user_id)
                )


def record_screentime_heartbeat(
    conn: sqlite3.Connection,
    user_id: str,
    active_s: float,
    idle_s: float = 0.0
) -> ScreenTimeHeartbeatResp:
    with tx(conn):
        user = conn.execute("SELECT * FROM users WHERE id = ?;", (user_id,)).fetchone()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error_code": "USER_NOT_FOUND", "message": "User not found"})

        # Record event
        ev_id = f"ste_{secrets.token_hex(8)}"
        conn.execute(
            """
            INSERT INTO screen_time_events (id, user_id, active_s, idle_s, source, recorded_at)
            VALUES (?, ?, ?, ?, 'web_active', CURRENT_TIMESTAMP);
            """,
            (ev_id, user_id, active_s, idle_s)
        )

        # Update user active screen time & streak
        new_total_screen = float(user["screen_time_total_s"] or 0.0) + active_s
        new_streak = float(user["current_screen_streak_s"] or 0.0) + active_s
        threshold_s = float(user["screen_time_threshold_s"] or 1800.0)
        outdoor_total = float(user["outdoor_time_total_s"] or 0.0)

        conn.execute(
            """
            UPDATE users
            SET screen_time_total_s = ?,
                current_screen_streak_s = ?,
                last_seen_at = CURRENT_TIMESTAMP
            WHERE id = ?;
            """,
            (new_total_screen, new_streak, user_id)
        )

        touch_grass_alert = new_streak >= threshold_s
        grass_debt_s = max(0.0, new_streak - threshold_s)

        total_time = outdoor_total + new_total_screen
        ratio = (outdoor_total / total_time) if total_time > 0 else 0.0

        if touch_grass_alert:
            over_mins = int(grass_debt_s / 60.0)
            msg = f"🌱 Touch Grass Alert! You've been on your screen for {int(new_streak/60)} mins (exceeding your {int(threshold_s/60)} min limit by {over_mins} mins). Step outside and collect loot!"
        else:
            left_mins = int(max(0.0, threshold_s - new_streak) / 60.0)
            msg = f"{left_mins} mins of screen time remaining before grass threshold."

        return ScreenTimeHeartbeatResp(
            screen_time_total_s=new_total_screen,
            current_screen_streak_s=new_streak,
            screen_time_threshold_s=threshold_s,
            outdoor_time_total_s=outdoor_total,
            touch_grass_alert=touch_grass_alert,
            touch_grass_ratio=round(ratio, 3),
            grass_debt_minutes=round(grass_debt_s / 60.0, 1),
            message=msg
        )


def get_screentime_summary(conn: sqlite3.Connection, user_id: str) -> dict:
    user = conn.execute("SELECT * FROM users WHERE id = ?;", (user_id,)).fetchone()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    out_s = float(user["outdoor_time_total_s"] or 0.0)
    scr_s = float(user["screen_time_total_s"] or 0.0)
    streak_s = float(user["current_screen_streak_s"] or 0.0)
    thresh_s = float(user["screen_time_threshold_s"] or 1800.0)
    total_s = out_s + scr_s
    ratio = (out_s / total_s) if total_s > 0 else 0.0
    debt_s = max(0.0, streak_s - thresh_s)
    return {
        "screen_time_total_s": scr_s,
        "current_screen_streak_s": streak_s,
        "screen_time_threshold_s": thresh_s,
        "outdoor_time_total_s": out_s,
        "outdoor_minutes": round(out_s / 60.0, 1),
        "screen_minutes": round(scr_s / 60.0, 1),
        "screen_streak_minutes": round(streak_s / 60.0, 1),
        "nudge_threshold_minutes": int(thresh_s / 60.0),
        "grass_ratio": round(ratio, 3),
        "touch_grass_alert": streak_s >= thresh_s,
        "grass_debt_minutes": round(debt_s / 60.0, 1)
    }


def import_digital_wellbeing(
    conn: sqlite3.Connection,
    user_id: str,
    daily_screen_hours: float,
    device_label: str
) -> ScreenTimeImportResp:
    with tx(conn):
        screen_seconds = daily_screen_hours * 3600.0
        ev_id = f"ste_{secrets.token_hex(8)}"
        conn.execute(
            """
            INSERT INTO screen_time_events (id, user_id, active_s, idle_s, source, recorded_at)
            VALUES (?, ?, ?, 0.0, ?, CURRENT_TIMESTAMP);
            """,
            (ev_id, user_id, screen_seconds, device_label)
        )

        user = conn.execute("SELECT * FROM users WHERE id = ?;", (user_id,)).fetchone()
        new_total_s = float(user["screen_time_total_s"] or 0.0) + screen_seconds
        # Increase current streak by half the imported hours to nudge walking
        new_streak = float(user["current_screen_streak_s"] or 0.0) + (screen_seconds * 0.5)

        conn.execute(
            """
            UPDATE users
            SET screen_time_total_s = ?,
                current_screen_streak_s = ?
            WHERE id = ?;
            """,
            (new_total_s, new_streak, user_id)
        )

        debt_mins = round((screen_seconds / 3600.0) * 15.0, 1) # 15 min walk per hour of screen time
        suggested_walk = max(15, int(debt_mins))

        return ScreenTimeImportResp(
            imported_hours=daily_screen_hours,
            total_screen_hours=round(new_total_s / 3600.0, 2),
            grass_debt_minutes=debt_mins,
            suggested_walk_mins=suggested_walk,
            message=f"Imported {daily_screen_hours}h from {device_label}. Your Grass Debt is {suggested_walk} outdoor walk minutes!"
        )


def update_threshold(conn: sqlite3.Connection, user_id: str, threshold_mins: int) -> float:
    with tx(conn):
        thresh_s = float(threshold_mins * 60)
        conn.execute("UPDATE users SET screen_time_threshold_s = ? WHERE id = ?;", (thresh_s, user_id))
        return thresh_s


def reset_screen_streak_after_walk(conn: sqlite3.Connection, user_id: str, walk_duration_s: float) -> None:
    with tx(conn):
        user = conn.execute("SELECT * FROM users WHERE id = ?;", (user_id,)).fetchone()
        if user:
            cur_outdoor = float(user["outdoor_time_total_s"] or 0.0) + walk_duration_s
            conn.execute(
                """
                UPDATE users
                SET outdoor_time_total_s = ?,
                    current_screen_streak_s = 0.0
                WHERE id = ?;
                """,
                (cur_outdoor, user_id)
            )


def add_friend(conn: sqlite3.Connection, user_id: str, friend_code_or_name: str) -> FriendItem:
    seed_demo_social_walkers_if_empty(conn, user_id)

    with tx(conn):
        # Find friend by id or display name
        friend = conn.execute(
            "SELECT * FROM users WHERE (id = ? OR LOWER(display_name) = LOWER(?)) AND id != ?;",
            (friend_code_or_name, friend_code_or_name.strip(), user_id)
        ).fetchone()

        if not friend:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "FRIEND_NOT_FOUND", "message": f"Explorer '{friend_code_or_name}' not found. Check user ID or name."}
            )

        friend_id = friend["id"]

        # Insert mutual friendship
        f_id1 = f"fr_{secrets.token_hex(6)}"
        f_id2 = f"fr_{secrets.token_hex(6)}"
        conn.execute(
            "INSERT OR IGNORE INTO friends (id, user_id, friend_id, status) VALUES (?, ?, ?, 'ACCEPTED');",
            (f_id1, user_id, friend_id)
        )
        conn.execute(
            "INSERT OR IGNORE INTO friends (id, user_id, friend_id, status) VALUES (?, ?, ?, 'ACCEPTED');",
            (f_id2, friend_id, user_id)
        )

        pts = get_points_balance(conn, friend_id)
        out_mins = round(float(friend["outdoor_time_total_s"] or 0.0) / 60.0, 1)
        screen_mins = round(float(friend["screen_time_total_s"] or 0.0) / 60.0, 1)
        total_m = out_mins + screen_mins
        ratio = round((out_mins / total_m), 3) if total_m > 0 else 0.0

        return FriendItem(
            user_id=friend_id,
            display_name=str(friend["display_name"]),
            avatar_emoji=str(friend["avatar_emoji"] or "🌱"),
            outdoor_mins=out_mins,
            screen_mins=screen_mins,
            touch_grass_ratio=ratio,
            points=pts,
            status_msg=str(friend["status_msg"] or "Ready to walk"),
            is_online=True,
            last_seen="Just now"
        )


def list_friends(conn: sqlite3.Connection, user_id: str) -> List[FriendItem]:
    seed_demo_social_walkers_if_empty(conn, user_id)

    rows = conn.execute(
        """
        SELECT u.*
        FROM friends f
        JOIN users u ON f.friend_id = u.id
        WHERE f.user_id = ? AND f.status = 'ACCEPTED'
        ORDER BY u.outdoor_time_total_s DESC;
        """,
        (user_id,)
    ).fetchall()

    result = []
    for r in rows:
        fid = r["id"]
        pts = get_points_balance(conn, fid)
        out_mins = round(float(r["outdoor_time_total_s"] or 0.0) / 60.0, 1)
        screen_mins = round(float(r["screen_time_total_s"] or 0.0) / 60.0, 1)
        total_m = out_mins + screen_mins
        ratio = round((out_mins / total_m), 3) if total_m > 0 else 0.0

        result.append(FriendItem(
            user_id=fid,
            display_name=str(r["display_name"]),
            avatar_emoji=str(r["avatar_emoji"] or "🌱"),
            outdoor_mins=out_mins,
            screen_mins=screen_mins,
            touch_grass_ratio=ratio,
            points=pts,
            status_msg=str(r["status_msg"] or "Ready to walk"),
            is_online=True,
            last_seen="Active today"
        ))
    return result


def send_nudge(conn: sqlite3.Connection, sender_id: str, receiver_id: str, message: str) -> str:
    with tx(conn):
        nudge_id = f"ndg_{secrets.token_hex(8)}"
        conn.execute(
            """
            INSERT INTO friend_nudges (id, sender_id, receiver_id, message, created_at, seen)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 0);
            """,
            (nudge_id, sender_id, receiver_id, message)
        )
        return nudge_id


def get_pending_nudges(conn: sqlite3.Connection, user_id: str) -> List[FriendNudgeItem]:
    rows = conn.execute(
        """
        SELECT n.*, u.display_name, u.avatar_emoji
        FROM friend_nudges n
        JOIN users u ON n.sender_id = u.id
        WHERE n.receiver_id = ? AND n.seen = 0
        ORDER BY n.created_at DESC;
        """,
        (user_id,)
    ).fetchall()

    nudges = []
    for r in rows:
        nudges.append(FriendNudgeItem(
            id=str(r["id"]),
            sender_id=str(r["sender_id"]),
            sender_name=str(r["display_name"]),
            sender_avatar=str(r["avatar_emoji"] or "🌱"),
            message=str(r["message"]),
            created_at=str(r["created_at"])
        ))
    
    # Mark as seen
    with tx(conn):
        conn.execute("UPDATE friend_nudges SET seen = 1 WHERE receiver_id = ?;", (user_id,))

    return nudges


def get_live_leaderboard(conn: sqlite3.Connection, current_user_id: str) -> LeaderboardResp:
    seed_demo_social_walkers_if_empty(conn, current_user_id)

    # Fetch all active users
    users = conn.execute("SELECT * FROM users WHERE status = 'ACTIVE';").fetchall()

    # Get user friend set
    friends = {r[0] for r in conn.execute("SELECT friend_id FROM friends WHERE user_id = ?;", (current_user_id,)).fetchall()}

    items: List[LeaderboardItem] = []
    for u in users:
        uid = u["id"]
        pts = get_points_balance(conn, uid)
        out_mins = round(float(u["outdoor_time_total_s"] or 0.0) / 60.0, 1)
        screen_mins = round(float(u["screen_time_total_s"] or 0.0) / 60.0, 1)
        total = out_mins + screen_mins
        ratio_pct = int(round((out_mins / total * 100))) if total > 0 else 0

        # Grass score formula: points + (outdoor_mins * 2)
        score = pts + int(out_mins * 2)

        items.append(LeaderboardItem(
            rank=0,
            user_id=uid,
            display_name=str(u["display_name"]),
            avatar_emoji=str(u["avatar_emoji"] or "🌱"),
            grass_score=score,
            points=pts,
            outdoor_mins=out_mins,
            screen_mins=screen_mins,
            ratio_percent=ratio_pct,
            is_friend=uid in friends,
            is_current_user=uid == current_user_id
        ))

    # Sort by grass_score descending
    items.sort(key=lambda x: (x.grass_score, x.ratio_percent, x.points), reverse=True)

    user_rank = 1
    for idx, it in enumerate(items, start=1):
        it.rank = idx
        if it.is_current_user:
            user_rank = idx

    return LeaderboardResp(
        leaderboard=items[:20],
        user_rank=user_rank,
        total_walkers=len(items),
        time_window="Live Real-Time"
    )
