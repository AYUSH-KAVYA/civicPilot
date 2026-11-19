"""
Authentication API Router.
POST /api/auth/login -> {token}
Source of truth: docs/CONTRACT.md Section 7.
"""

from fastapi import APIRouter, HTTPException, status

from backend.app.core.auth import create_officer_token
from backend.app.core.config import get_settings
from backend.app.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest) -> LoginResponse:
    """Authenticate municipal officer via password."""
    settings = get_settings()
    if req.password != settings.OFFICER_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid officer password",
        )
    token = create_officer_token(officer_id="admin-officer", role="officer")
    return LoginResponse(token=token)
