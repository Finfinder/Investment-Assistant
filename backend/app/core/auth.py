"""JWT authentication dependency for FastAPI endpoints.

Usage in endpoints:
    from app.core.auth import require_auth

    @router.get("/protected")
    async def protected(user: str = Depends(require_auth)):
        ...

Usage in WebSocket:
    from app.core.auth import ws_require_auth

    @router.websocket("/ws/{id}")
    async def ws_endpoint(websocket: WebSocket, token: str):
        user: str = ws_require_auth(token)
        ...
"""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from argon2.exceptions import VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException, WebSocketException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{get_settings().API_V1_PREFIX}/auth/token"
)

_TOKEN_ISSUER = "investment-assistant"  # noqa: S105


class TokenData(BaseModel):
    sub: str


def create_access_token(data: dict[str, object], expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    to_encode = data.copy()
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = expire
    to_encode["iat"] = now
    to_encode["iss"] = _TOKEN_ISSUER
    to_encode["jti"] = str(uuid4())
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> TokenData:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            issuer=_TOKEN_ISSUER,
            options={"require": ["exp", "sub", "iat", "iss"]},
        )
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(
                status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"}
            )
        return TokenData(sub=sub)
    except jwt.ExpiredSignatureError as err:
        raise HTTPException(
            status_code=401, detail="Token has expired", headers={"WWW-Authenticate": "Bearer"}
        ) from err
    except (jwt.InvalidTokenError, jwt.DecodeError) as err:
        raise HTTPException(
            status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"}
        ) from err


async def require_auth(token: str = Depends(oauth2_scheme)) -> str:
    token_data = verify_token(token)
    return token_data.sub


def ws_require_auth(token: str) -> str:
    if not token:
        raise WebSocketException(code=1008, reason="Authentication required")
    try:
        token_data = verify_token(token)
    except HTTPException as exc:
        raise WebSocketException(code=1008, reason=exc.detail) from exc
    return token_data.sub


def authenticate_user(username: str, password: str) -> str | None:
    settings = get_settings()
    if settings.AUTH_USERNAME == "":
        logger.warning("Authentication attempted but AUTH_USERNAME not configured")
        return None

    # Constant-time username comparison to prevent timing-based enumeration
    username_match = secrets.compare_digest(username, settings.AUTH_USERNAME)

    if not username_match:
        # Perform dummy hash verification to equalize response time
        if settings.AUTH_PASSWORD_HASH:
            try:
                from pwdlib import PasswordHash

                pwdh = PasswordHash.recommended()
                pwdh.verify(password, settings.AUTH_PASSWORD_HASH)
            except (VerificationError, VerifyMismatchError, ValueError, TypeError):
                pass
        logger.warning("Failed login attempt for unknown user: %s", username)
        return None

    if settings.AUTH_PASSWORD_HASH == "":
        logger.warning("Failed login attempt for user: %s", username)
        return None

    from pwdlib import PasswordHash

    try:
        pwdh = PasswordHash.recommended()
        pwdh.verify(password, settings.AUTH_PASSWORD_HASH)
        return username
    except (VerificationError, VerifyMismatchError, ValueError, TypeError):
        logger.warning("Failed login attempt for user: %s - invalid password", username)
        return None


def hash_password(password: str) -> str:
    from pwdlib import PasswordHash

    pwdh = PasswordHash.recommended()
    return pwdh.hash(password)
