import os
import uuid
from typing import Optional

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, schemas
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.database import get_async_session
from ..db.user import User

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET environment variable is required. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )
JWT_LIFETIME = int(os.getenv("JWT_LIFETIME_SECONDS", str(60 * 60 * 24)))  # 24 h


# ── Pydantic schemas ────────────────────────────────────────────────────────

class UserRead(schemas.BaseUser[uuid.UUID]):
    pass


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass


# ── Database adapter ────────────────────────────────────────────────────────

async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)


# ── User manager ────────────────────────────────────────────────────────────

class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = JWT_SECRET
    verification_token_secret = JWT_SECRET

    async def create(self, user_create, safe: bool = False, request: Optional[Request] = None):
        from sqlalchemy import func, select

        result = await self.user_db.session.execute(
            select(func.count()).select_from(User)
        )
        count = result.scalar()

        if count == 0:
            # First registered user becomes superuser automatically
            try:
                user_create = user_create.model_copy(
                    update={"is_superuser": True, "is_verified": True}
                )
            except AttributeError:  # Pydantic v1 fallback
                user_create = user_create.copy(
                    update={"is_superuser": True, "is_verified": True}
                )
            return await super().create(user_create, safe=False, request=request)

        return await super().create(user_create, safe=safe, request=request)

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        role = "superuser" if user.is_superuser else "user"
        print(f"[auth] New {role} registered: {user.email}")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"[auth] Password reset requested for {user.email}. Token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"[auth] Verification requested for {user.email}. Token: {token}")


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)


# ── JWT auth backend ────────────────────────────────────────────────────────

bearer_transport = BearerTransport(tokenUrl="/api/auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=JWT_SECRET, lifetime_seconds=JWT_LIFETIME)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# ── FastAPIUsers instance ───────────────────────────────────────────────────

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)


async def get_user_from_query_token(
    request: Request,
    user_manager: UserManager = Depends(get_user_manager),
) -> User:
    """Validates a JWT passed as ?token= query param (used for media src= URLs)."""
    from fastapi import HTTPException
    token = request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    strategy = get_jwt_strategy()
    user = await strategy.read_token(token, user_manager)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user
