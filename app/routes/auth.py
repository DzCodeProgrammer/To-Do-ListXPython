from fastapi import APIRouter, status

from app.cache.rate_limit import RateLimiter, private_identity
from app.cache.redis import get_redis
from app.config import settings
from app.dependencies import AuthServiceDep, CurrentUser
from app.schemas.auth import Token, UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


async def auth_rate_limit(identity: str, scope: str) -> None:
    await RateLimiter(get_redis()).check(
        private_identity(identity), scope, settings.auth_rate_limit_requests,
        settings.rate_limit_window_seconds,
    )


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
)
async def register(data: UserCreate, service: AuthServiceDep):
    await auth_rate_limit(data.email, "auth-register")
    return await service.register(data)


@router.post("/login", response_model=Token)
async def login(data: UserLogin, service: AuthServiceDep) -> Token:
    await auth_rate_limit(data.email, "auth-login")
    return await service.login(data)


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser):
    return user
