"""
Authentication & Authorization for CivicPilot.
Handles JWT auth for city officers and case-scoped tokens for citizens.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.core.config import get_settings

security = HTTPBearer(auto_error=False)


def create_officer_token(officer_id: str = "officer-admin", role: str = "officer") -> str:
    """Generate JWT token for an authenticated municipal officer."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": officer_id,
        "role": role,
        "type": "officer",
        "iat": now,
        "exp": now + timedelta(hours=settings.JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_officer_token(token: str) -> Dict[str, Any]:
    """Decode and validate an officer JWT."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "officer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type: expected officer token",
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Officer token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid officer token",
        )


def create_case_access_token(case_id: str) -> str:
    """Generate a scoped access token for the citizen who filed this specific case."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": f"case:{case_id}",
        "case_id": case_id,
        "type": "citizen",
        "iat": now,
        "exp": now + timedelta(days=settings.CITIZEN_TOKEN_EXPIRATION_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_case_access_token(token: str, expected_case_id: Optional[str] = None) -> str:
    """Validate a case-scoped token and return the associated case_id."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "citizen":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid token type: expected citizen case token",
            )
        case_id = payload.get("case_id")
        if not case_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token missing case_id claim",
            )
        if expected_case_id and case_id != expected_case_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token not valid for this case",
            )
        return case_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Case access token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid case access token",
        )


async def get_current_officer(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """Dependency: require a valid officer JWT in the Authorization: Bearer header."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Officer authorization required (Bearer token missing)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_officer_token(credentials.credentials)


async def require_case_or_officer_access(
    id: Optional[str] = None,
    case_id: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    x_case_token: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """
    Dependency: ensure caller is either:
    1. A municipal officer with valid Bearer JWT, OR
    2. A citizen with a valid case-scoped token for this specific case.
    Accepts path parameter as either 'id' or 'case_id'.
    """
    target_id = case_id or id

    # 1. Check Authorization: Bearer <token>
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        settings = get_settings()
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            # If officer token:
            if payload.get("type") == "officer":
                return {"type": "officer", "payload": payload}
            # If citizen token:
            if payload.get("type") == "citizen" and payload.get("case_id") == target_id:
                return {"type": "citizen", "case_id": target_id}
        except jwt.InvalidTokenError:
            pass  # try x_case_token or fail below

    # 2. Check X-Case-Token header or query param
    if x_case_token:
        try:
            cid = verify_case_access_token(x_case_token, expected_case_id=target_id)
            return {"type": "citizen", "case_id": cid}
        except HTTPException:
            raise

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: valid officer token or matching case access token required",
    )
