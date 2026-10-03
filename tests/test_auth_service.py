import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.schemas.auth import UserLogin
from app.security import hash_password
from app.services.auth import AuthService


@pytest.mark.asyncio
async def test_login_returns_token_and_user_in_one_response():
    user = SimpleNamespace(
        id=uuid.uuid4(),
        email="user@example.com",
        password_hash=hash_password("strong-password"),
        created_at=datetime.now(UTC),
    )
    repository = SimpleNamespace(get_by_email=AsyncMock(return_value=user))

    result = await AuthService(repository).login(
        UserLogin(email="user@example.com", password="strong-password")
    )

    assert result.access_token
    assert result.user.id == user.id
    assert result.user.email == user.email
    repository.get_by_email.assert_awaited_once_with("user@example.com")
