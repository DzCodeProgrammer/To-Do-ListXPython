from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.repositories.user import UserRepository
from app.schemas.auth import Token, UserCreate, UserLogin
from app.security import create_access_token, hash_password, verify_password


class AuthService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def register(self, data: UserCreate):
        email = data.email.lower()
        if await self.repository.get_by_email(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
            )
        try:
            return await self.repository.create(email, hash_password(data.password))
        except IntegrityError as exc:
            await self.repository.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
            ) from exc

    async def login(self, data: UserLogin) -> Token:
        user = await self.repository.get_by_email(data.email.lower())
        if not user or not verify_password(data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return Token(access_token=create_access_token(user.id), user=user)
