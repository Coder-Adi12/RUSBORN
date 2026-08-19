"""Authentication middleware for the RUSBORN API.

Two tiers of protection:
1. Internal API secret  — for agent→backend calls (appointments, webhooks, knowledge)
2. Dashboard session    — for browser-based dashboard access (cookie-based)
"""

import hashlib
import hmac
import logging
import secrets
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from config import settings

logger = logging.getLogger(__name__)

# ── In-memory session store ───────────────────────────────────────────────────
# In production, consider Redis or a DB-backed store. For a single-instance
# deployment this is sufficient and avoids extra dependencies.
_sessions: dict[str, str] = {}  # session_token → username

INTERNAL_SECRET_HEADER = "X-Internal-Secret"


# ── Dependencies ──────────────────────────────────────────────────────────────


def require_internal_secret(request: Request) -> None:
    """Reject requests that don't carry a valid internal API secret.

    Used for agent→backend routes (appointments, webhooks, knowledge).
    """
    secret = settings.internal_api_secret
    if not secret:
        # If no secret is configured (dev convenience), skip enforcement.
        return

    provided = request.headers.get(INTERNAL_SECRET_HEADER, "")
    if not hmac.compare_digest(provided, secret):
        raise HTTPException(status_code=401, detail="Invalid or missing internal API secret")


def require_dashboard_session(request: Request) -> str:
    """Reject requests without a valid dashboard session cookie.

    Returns the authenticated username.
    """
    token: Optional[str] = request.cookies.get("dashboard_session")
    if not token or token not in _sessions:
        raise HTTPException(status_code=401, detail="Authentication required")
    return _sessions[token]


# ── Auth router ───────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(req: LoginRequest, response: Response) -> dict:
    """Authenticate a dashboard operator and set a session cookie."""
    expected_user = settings.dashboard_username
    expected_pass = settings.dashboard_password

    if not expected_user or not expected_pass:
        raise HTTPException(
            status_code=503,
            detail="Dashboard credentials not configured",
        )

    # Constant-time comparison to prevent timing attacks
    user_ok = hmac.compare_digest(req.username, expected_user)
    pass_ok = hmac.compare_digest(
        hashlib.sha256(req.password.encode()).hexdigest(),
        hashlib.sha256(expected_pass.encode()).hexdigest(),
    )

    if not (user_ok and pass_ok):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = secrets.token_urlsafe(32)
    _sessions[token] = req.username
    is_prod = settings.environment in ("production", "staging")
    response.set_cookie(
        key="dashboard_session",
        value=token,
        httponly=True,
        secure=is_prod,
        samesite="lax" if not is_prod else "none",
        max_age=86400,  # 24 hours
    )
    return {"status": "ok", "username": req.username}


@router.post("/logout")
async def logout(request: Request, response: Response) -> dict:
    """Destroy the dashboard session."""
    token = request.cookies.get("dashboard_session")
    if token and token in _sessions:
        del _sessions[token]
    response.delete_cookie("dashboard_session")
    return {"status": "ok"}
