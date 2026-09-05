import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Callable
from fastapi import Header, HTTPException, status
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "default-jwt-secret-hospital-optimizer")
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 8

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")
STAFF_ACCESS_CODE = os.getenv("STAFF_ACCESS_CODE", "staff123")

def login_with_role(password: str, expected_password: str, role: str) -> str:
    """
    Validates provided password against expected password and returns a signed JWT.
    Raises HTTPException(401) on failure.
    """
    if not password or password != expected_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please check your password/access code."
        )

    now = datetime.now(timezone.utc)
    payload = {
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=TOKEN_EXPIRY_HOURS)).timestamp())
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

def decode_token(token: str) -> dict:
    """
    Decodes and validates a JWT token. Raises 401 if invalid or expired.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired. Please log in again."
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token."
        )

def require_role(required_role: str) -> Callable:
    """
    Returns a FastAPI dependency that enforces a strict role requirement.
    Checks Authorization: Bearer <token>.
    Raises 401 for missing/invalid token, 403 for insufficient role permissions.
    """
    def dependency(authorization: Optional[str] = Header(None)) -> dict:
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization header."
            )

        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed Authorization header. Format must be: Bearer <token>"
            )

        token = parts[1]
        payload = decode_token(token)

        role = payload.get("role")
        if role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Access requires '{required_role}' role permissions."
            )

        return payload

    return dependency
