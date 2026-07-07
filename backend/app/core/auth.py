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
from functools import lru_cache
from uuid import uuid4

import jwt
from argon2.exceptions import VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException, WebSocketException
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from pydantic import BaseModel

from app.core.config import get_settings


@lru_cache(maxsize=1)
def _get_password_hasher() -> PasswordHash:
    """Return a singleton PasswordHash instance.

    This avoids repeated initialization of the recommended hasher
    configuration on every authentication call.
    """
    return PasswordHash.recommended()


logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{get_settings().API_V1_PREFIX}/auth/token")

_TOKEN_ISSUER = "investment-assistant"  # noqa: S105


class TokenData(BaseModel):
    sub: str


def create_access_token(data: dict[str, object], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token for the given data.

    Args:
        data: Dictionary containing claims to encode in the token.
              Must include 'sub' (subject/username).
        expires_delta: Optional custom expiration time. If not provided,
                      uses the default from settings.ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        Encoded JWT string.

    The token includes standard claims:
    - exp: Expiration timestamp
    - iat: Issued at timestamp
    - iss: Token issuer ("investment-assistant")
    - jti: Unique token identifier for potential revocation
    """
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
    """Verify and decode a JWT access token.

    Args:
        token: The JWT string to verify.

    Returns:
        TokenData containing the subject (sub) claim.

    Raises:
        HTTPException: 401 if token is expired, invalid, or missing required claims.

    Validates:
    - Token signature using SECRET_KEY
    - Token expiration (exp claim)
    - Token issuer (iss claim must match "investment-assistant")
    - Required claims: exp, sub, iat, iss
    """
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
    """Validate access token and return authenticated username.

    Dependency for FastAPI endpoints that require authentication.

    Args:
        token: JWT access token from the Authorization header.
               Automatically extracted by OAuth2PasswordBearer.

    Returns:
        The username (sub claim) from the validated token.

    Raises:
        HTTPException: 401 if token is missing, invalid, or expired.

    Usage:
        @router.get("/protected")
        async def protected(user: str = Depends(require_auth)):
            ...
    """
    token_data = verify_token(token)
    return token_data.sub


def ws_require_auth(token: str | None) -> str:
    """Validate access token for WebSocket connections and return username.

    Args:
        token: JWT access token from the WebSocket connection.
               Can be None if authentication was not provided.

    Returns:
        The username (sub claim) from the validated token.

    Raises:
        WebSocketException: 1008 if token is missing, invalid, or expired.

    Usage:
        @router.websocket("/ws/{id}")
        async def ws_endpoint(websocket: WebSocket, token: str):
            user: str = ws_require_auth(token)
            ...
    """
    if not token:
        raise WebSocketException(code=1008, reason="Authentication required")
    try:
        token_data = verify_token(token)
    except HTTPException as exc:
        raise WebSocketException(code=1008, reason=exc.detail) from exc
    return token_data.sub


def authenticate_user(username: str, password: str) -> str | None:
    """Authenticate a user with username and password.

    Args:
        username: The username to authenticate.
        password: The password to verify.

    Returns:
        The username if authentication succeeds, None otherwise.

    Security notes:
    - Uses constant-time comparison for usernames to prevent timing attacks
    - Performs dummy hash verification for invalid usernames to equalize response times
    - All failed attempts are logged for security monitoring
    """
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
                pwdh = _get_password_hasher()
                pwdh.verify(password, settings.AUTH_PASSWORD_HASH)
            except (VerificationError, VerifyMismatchError, ValueError, TypeError):
                pass
        logger.warning("Failed login attempt for unknown user: %s", username)
        return None

    if settings.AUTH_PASSWORD_HASH == "":
        logger.warning("Failed login attempt for user: %s", username)
        return None

    try:
        pwdh = _get_password_hasher()
        pwdh.verify(password, settings.AUTH_PASSWORD_HASH)
        return username
    except (VerificationError, VerifyMismatchError, ValueError, TypeError):
        logger.warning("Failed login attempt for user: %s - invalid password", username)
        return None


def hash_password(password: str) -> str:
    """Hash a password for secure storage.

    Args:
        password: The plaintext password to hash.

    Returns:
        The hashed password string.

    Uses the recommended password hashing algorithm (Argon2)
    via the singleton hasher instance for efficiency.
    """
    pwdh = _get_password_hasher()
    return pwdh.hash(password)
