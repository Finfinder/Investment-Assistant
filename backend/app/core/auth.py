"""Authentication dependency — placeholder for future JWT integration.

Usage in endpoints:
    from app.core.auth import require_auth

    @router.get("/protected")
    async def protected(user: str = Depends(require_auth)):
        ...

To enable JWT auth, replace the body of ``require_auth`` with actual
token verification logic (e.g. python-jose / PyJWT).  No other files
need to change — all endpoints already accept ``Depends(require_auth)``.
"""

from fastapi import Request


async def require_auth(request: Request) -> str:
    """Validate the current request and return a user identifier.

    Currently a no-op that returns "anonymous" — swap out for real JWT
    verification when authentication is enabled.
    """
    return "anonymous"
