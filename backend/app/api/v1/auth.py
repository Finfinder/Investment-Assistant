"""REST API endpoint for JWT token issuance."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.core.auth import authenticate_user, create_access_token
from app.core.rate_limit import limiter

_TOKEN_TYPE_BEARER = "bearer"  # noqa: S105

_form_data_depends = Depends(OAuth2PasswordRequestForm)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


@router.post("/auth/token", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login_for_access_token(
    request: Request, form_data: OAuth2PasswordRequestForm = _form_data_depends
) -> TokenResponse:
    """Authenticate and obtain a JWT access token.

    Send username and password as form data to receive a Bearer token.
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user})
    logger.info("Token issued for user: %s", user)
    return TokenResponse(access_token=access_token, token_type=_TOKEN_TYPE_BEARER)
