"""JWT verification and the two dependencies almost every route needs:

get_db (a scoped SQLAlchemy session) and get_current_user (the caller's verified
identity). Nothing here ever trusts a value the client sent outside the token —
see auth/permissions.py for the org-membership and role checks built on top of it.
"""

import uuid
from collections.abc import Generator

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy.orm import Session

from auth.schemas import AuthenticatedUser
from core.config import get_settings
from database.connection import SessionLocal

_bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class _JWKSVerifier:
    """Wraps PyJWKClient so the JWKS document is fetched once and cached, not

    re-fetched on every request. PyJWKClient itself already caches by kid; this
    just gives us one shared instance per process instead of one per request.
    """

    def __init__(self) -> None:
        self._client: PyJWKClient | None = None

    def _get_client(self) -> PyJWKClient:
        if self._client is None:
            settings = get_settings()
            if not settings.supabase_url:
                raise RuntimeError("SUPABASE_URL is not configured — cannot verify tokens.")
            self._client = PyJWKClient(settings.jwks_url, cache_keys=True, lifespan=3600)
        return self._client

    def verify(self, token: str) -> dict:
        settings = get_settings()
        client = self._get_client()
        try:
            signing_key = client.get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256"],
                audience=settings.supabase_jwt_audience,
                options={"require": ["exp", "sub"]},
                # Tolerate a few seconds of clock drift between this server and
                # Supabase's — without it, a token can be legitimately rejected
                # as "not yet valid" purely because of clock skew, not because
                # anything is actually wrong with it.
                leeway=30,
            )
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session. Please sign in again.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc


_verifier = _JWKSVerifier()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = _verifier.verify(credentials.credentials)

    try:
        user_id = uuid.UUID(str(claims["sub"]))
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing a valid subject.",
        ) from exc

    return AuthenticatedUser(id=user_id, email=claims.get("email"))
