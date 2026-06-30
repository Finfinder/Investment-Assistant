"""Unit tests for JWT authentication module."""

from datetime import timedelta

import jwt
import pytest
from fastapi import HTTPException, WebSocketException

from app.core.auth import (
    authenticate_user,
    create_access_token,
    hash_password,
    require_auth,
    verify_token,
    ws_require_auth,
)
from app.core.config import get_settings


class TestCreateAccessToken:
    def test_returns_valid_jwt(self):
        token = create_access_token(data={"sub": "testuser"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_contains_correct_subject(self):
        token = create_access_token(data={"sub": "dev"})
        payload = jwt.decode(token, get_settings().SECRET_KEY, algorithms=[get_settings().ALGORITHM])
        assert payload["sub"] == "dev"

    def test_contains_exp_claim(self):
        token = create_access_token(data={"sub": "dev"})
        payload = jwt.decode(token, get_settings().SECRET_KEY, algorithms=[get_settings().ALGORITHM])
        assert "exp" in payload

    def test_custom_expiry(self):
        token = create_access_token(data={"sub": "dev"}, expires_delta=timedelta(minutes=5))
        payload = jwt.decode(token, get_settings().SECRET_KEY, algorithms=[get_settings().ALGORITHM])
        assert "exp" in payload


class TestVerifyToken:
    def test_valid_token(self):
        token = create_access_token(data={"sub": "dev"})
        result = verify_token(token)
        assert result.sub == "dev"

    def test_expired_token(self):
        token = create_access_token(data={"sub": "dev"}, expires_delta=timedelta(minutes=-1))
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail

    def test_invalid_signature(self):
        settings = get_settings()
        token = jwt.encode({"sub": "dev", "exp": 9999999999}, "wrong-key", algorithm=settings.ALGORITHM)
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == 401

    def test_malformed_token(self):
        with pytest.raises(HTTPException) as exc_info:
            verify_token("not-a-jwt")
        assert exc_info.value.status_code == 401

    def test_missing_sub_claim(self):
        settings = get_settings()
        token = jwt.encode({"exp": 9999999999}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == 401


class TestRequireAuth:
    @pytest.mark.asyncio
    async def test_returns_username(self):
        token = create_access_token(data={"sub": "dev"})
        result = await require_auth(token=token)
        assert result == "dev"

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            await require_auth(token="invalid")
        assert exc_info.value.status_code == 401


class TestWsRequireAuth:
    def test_valid_token(self):
        token = create_access_token(data={"sub": "dev"})
        result = ws_require_auth(token)
        assert result == "dev"

    def test_empty_token_raises_websocket_exception(self):
        with pytest.raises(WebSocketException) as exc_info:
            ws_require_auth("")
        assert exc_info.value.code == 1008

    def test_invalid_token_raises_websocket_exception(self):
        with pytest.raises(WebSocketException) as exc_info:
            ws_require_auth("invalid")
        assert exc_info.value.code == 1008


class TestAuthenticateUser:
    def test_correct_credentials(self):
        import unittest.mock as mock

        from app.core.auth import hash_password

        hashed = hash_password("dev-password")
        with mock.patch("app.core.auth.get_settings") as mock_settings:
            mock_settings.return_value.AUTH_USERNAME = "dev"
            mock_settings.return_value.AUTH_PASSWORD_HASH = hashed
            result = authenticate_user("dev", "dev-password")
            assert result == "dev"

    def test_wrong_password(self):
        result = authenticate_user("dev", "wrong")
        assert result is None

    def test_unknown_user(self):
        result = authenticate_user("unknown", "dev")
        assert result is None


class TestHashPassword:
    def test_returns_hash(self):
        hashed = hash_password("test-password")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_verifiable(self):
        from pwdlib import PasswordHash

        password = "my-secret-password"  # noqa: S105
        hashed = hash_password(password)
        pwdh = PasswordHash.recommended()
        pwdh.verify(password, hashed)
