import hashlib
import secrets
import time
from collections import defaultdict
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from server.db import get_db, tx
from server.schemas import (
    AnonAuthResponse,
    AuthResponse,
    ErrorResponse,
    LoginReq,
    ProfileResponse,
    ProfileUpdateReq,
    RegisterReq,
)
from server.settings import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory token bucket rate limiter
# ip/token -> list of request timestamps
_rate_limit_records: Dict[str, List[float]] = defaultdict(list)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def check_rate_limit(key: str, max_requests: int = 60, window_s: float = 60.0) -> None:
    now = time.time()
    records = _rate_limit_records[key]
    # Prune old records
    cutoff = now - window_s
    _rate_limit_records[key] = [t for t in records if t > cutoff]
    if len(_rate_limit_records[key]) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error_code": "RATE_LIMITED", "message": "Too many requests. Please slow down.", "retry_after_s": 10.0}
        )
    _rate_limit_records[key].append(now)


def get_current_user_id(
    request: Request,
    authorization: Optional[str] = Header(None)
) -> str:
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "AUTH_REQUIRED", "message": "Missing or invalid Bearer token"}
        )

    raw_token = authorization.split(" ", 1)[1].strip()
    token_hashed = hash_token(raw_token)

    # Check rate limit per token/ip
    check_rate_limit(f"user:{token_hashed}", max_requests=settings.rate_limit_per_minute)

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT u.id, u.status
            FROM installations i
            JOIN users u ON i.user_id = u.id
            WHERE i.token_hash = ?
            """,
            (token_hashed,)
        ).fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error_code": "INVALID_TOKEN", "message": "Provided token is unrecognized or revoked"}
            )

        if row["status"] != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error_code": "USER_INACTIVE", "message": "User account is suspended"}
            )

        # Update last seen timestamp
        conn.execute(
            "UPDATE installations SET last_seen = CURRENT_TIMESTAMP WHERE token_hash = ?",
            (token_hashed,)
        )
        conn.commit()
        return str(row["id"])


@router.post("/anon", response_model=AnonAuthResponse)
def create_anonymous_user(request: Request):
    client_ip = request.client.host if request.client else "127.0.0.1"
    check_rate_limit(f"anon:{client_ip}", max_requests=30)

    user_id = f"usr_{secrets.token_hex(8)}"
    installation_id = f"inst_{secrets.token_hex(8)}"
    raw_token = f"tgt_{secrets.token_urlsafe(32)}"
    token_hashed = hash_token(raw_token)
    display_name = f"Walker {secrets.token_hex(2).upper()}"

    with get_db() as conn:
        with tx(conn):
            conn.execute(
                "INSERT INTO users (id, display_name, status) VALUES (?, ?, 'ACTIVE')",
                (user_id, display_name)
            )
            conn.execute(
                "INSERT INTO installations (id, user_id, token_hash) VALUES (?, ?, ?)",
                (installation_id, user_id, token_hashed)
            )

    return AnonAuthResponse(
        user_id=user_id,
        token=raw_token,
        display_name=display_name
    )


@router.post("/register", response_model=AuthResponse)
def register_user(
    payload: RegisterReq,
    request: Request,
    authorization: Optional[str] = Header(None)
):
    from server.services.profile import hash_password
    from server.services.points import get_points_balance

    uname = payload.username.strip().lower()
    if not uname or len(uname) < 3:
        raise HTTPException(status_code=400, detail={"error_code": "INVALID_USERNAME", "message": "Username must be at least 3 characters."})

    with get_db() as conn:
        with tx(conn):
            # Check existing username
            existing = conn.execute("SELECT id FROM users WHERE LOWER(username) = ?;", (uname,)).fetchone()
            if existing:
                raise HTTPException(status_code=400, detail={"error_code": "USERNAME_TAKEN", "message": f"Username '{payload.username}' is already taken."})

            # Check if there is an existing anonymous user in session to upgrade
            upgraded_user_id = None
            if authorization and authorization.startswith("Bearer "):
                raw_tok = authorization.split(" ", 1)[1].strip()
                tok_h = hash_token(raw_tok)
                inst = conn.execute("SELECT user_id FROM installations WHERE token_hash = ?;", (tok_h,)).fetchone()
                if inst:
                    cur_u = conn.execute("SELECT id, username FROM users WHERE id = ?;", (inst["user_id"],)).fetchone()
                    if cur_u and not cur_u["username"]:
                        upgraded_user_id = cur_u["id"]

            user_id = upgraded_user_id or f"usr_{secrets.token_hex(8)}"
            disp_name = payload.display_name.strip() if payload.display_name and payload.display_name.strip() else payload.username.strip()
            hashed, salt = hash_password(payload.password)
            pw_record = f"{salt}:{hashed}"

            if upgraded_user_id:
                conn.execute(
                    "UPDATE users SET username = ?, password_hash = ?, display_name = ? WHERE id = ?;",
                    (uname, pw_record, disp_name, user_id)
                )
            else:
                conn.execute(
                    "INSERT INTO users (id, username, password_hash, display_name, status) VALUES (?, ?, ?, ?, 'ACTIVE');",
                    (user_id, uname, pw_record, disp_name)
                )

            # Generate fresh token
            raw_token = f"tgt_{secrets.token_urlsafe(32)}"
            token_hashed = hash_token(raw_token)
            inst_id = f"inst_{secrets.token_hex(8)}"
            conn.execute(
                "INSERT INTO installations (id, user_id, token_hash) VALUES (?, ?, ?);",
                (inst_id, user_id, token_hashed)
            )

            pts = get_points_balance(conn, user_id)
            user_row = conn.execute("SELECT * FROM users WHERE id = ?;", (user_id,)).fetchone()

    return AuthResponse(
        user_id=user_id,
        token=raw_token,
        username=uname,
        display_name=disp_name,
        avatar_emoji=str(user_row["avatar_emoji"] if "avatar_emoji" in user_row.keys() and user_row["avatar_emoji"] else "🌱"),
        bio=str(user_row["bio"] if "bio" in user_row.keys() and user_row["bio"] else "Outdoor trail explorer"),
        points=pts
    )


@router.post("/login", response_model=AuthResponse)
def login_user(payload: LoginReq, request: Request):
    from server.services.profile import verify_password
    from server.services.points import get_points_balance

    uname = payload.username.strip().lower()
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE LOWER(username) = ?;", (uname,)).fetchone()
        if not user or not user["password_hash"] or not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error_code": "INVALID_CREDENTIALS", "message": "Incorrect username or password"}
            )

        user_id = str(user["id"])
        raw_token = f"tgt_{secrets.token_urlsafe(32)}"
        token_hashed = hash_token(raw_token)
        inst_id = f"inst_{secrets.token_hex(8)}"
        with tx(conn):
            conn.execute(
                "INSERT INTO installations (id, user_id, token_hash) VALUES (?, ?, ?);",
                (inst_id, user_id, token_hashed)
            )

        pts = get_points_balance(conn, user_id)

    return AuthResponse(
        user_id=user_id,
        token=raw_token,
        username=uname,
        display_name=str(user["display_name"] or uname),
        avatar_emoji=str(user["avatar_emoji"] if "avatar_emoji" in user.keys() and user["avatar_emoji"] else "🌱"),
        bio=str(user["bio"] if "bio" in user.keys() and user["bio"] else "Outdoor trail explorer"),
        points=pts
    )


@router.get("/me", response_model=AuthResponse)
def get_me(user_id: str = Depends(get_current_user_id)):
    from server.services.points import get_points_balance
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?;", (user_id,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        pts = get_points_balance(conn, user_id)

    return AuthResponse(
        user_id=user_id,
        token="",
        username=user["username"] if "username" in user.keys() else None,
        display_name=str(user["display_name"] or "Trail Walker"),
        avatar_emoji=str(user["avatar_emoji"] if "avatar_emoji" in user.keys() and user["avatar_emoji"] else "🌱"),
        bio=str(user["bio"] if "bio" in user.keys() and user["bio"] else "Outdoor trail explorer"),
        points=pts
    )


@router.get("/verify")
def verify_token(user_id: str = Depends(get_current_user_id)):
    return {"user_id": user_id, "status": "authenticated"}


@router.get("/profile", response_model=ProfileResponse)
def get_my_profile(user_id: str = Depends(get_current_user_id)):
    from server.services.profile import get_user_profile
    with get_db() as conn:
        return get_user_profile(conn, user_id)


@router.post("/profile/update", response_model=ProfileResponse)
def update_my_profile(
    payload: ProfileUpdateReq,
    user_id: str = Depends(get_current_user_id)
):
    from server.services.profile import update_user_profile
    with get_db() as conn:
        return update_user_profile(conn, user_id, payload)

