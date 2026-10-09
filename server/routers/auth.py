import hashlib
import secrets
import time
from collections import defaultdict
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from server.db import get_db, tx
from server.schemas import AnonAuthResponse, ErrorResponse
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


@router.get("/verify")
def verify_token(user_id: str = Depends(get_current_user_id)):
    return {"user_id": user_id, "status": "authenticated"}
