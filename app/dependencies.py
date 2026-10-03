import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis import get_redis
from app.cache.task_cache import TaskCache
from app.database.session import get_db
from app.models.user import User
from app.repositories.task import TaskRepository
from app.repositories.user import UserRepository
from app.security import decode_access_token
from app.services.auth import AuthService
from app.services.task import TaskService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

DbSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis)]


def get_auth_service(db: DbSession) -> AuthService:
    return AuthService(UserRepository(db))


def get_task_service(db: DbSession, redis: RedisClient) -> TaskService:
    return TaskService(TaskRepository(db), TaskCache(redis))


async def get_current_user(
    db: DbSession, token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id: uuid.UUID = decode_access_token(token)
    except (jwt.InvalidTokenError, ValueError):
        raise credentials_error from None
    user = await UserRepository(db).get_by_id(user_id)
    if not user:
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
