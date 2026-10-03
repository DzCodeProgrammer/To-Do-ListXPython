import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from pydantic import ValidationError

from app.cache.rate_limit import private_identity
from app.config import settings
from app.schemas.auth import UserCreate
from app.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_and_verify():
    hashed = hash_password("strong-password")
    assert hashed != "strong-password"
    assert verify_password("strong-password", hashed)
    assert not verify_password("wrong-password", hashed)


def test_jwt_round_trip():
    user_id = uuid.uuid4()
    assert decode_access_token(create_access_token(user_id)) == user_id


def test_jwt_rejects_token_without_required_issuer_and_audience():
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "exp": datetime.now(UTC) + timedelta(minutes=5)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)


def test_signup_rejects_short_password():
    with pytest.raises(ValidationError):
        UserCreate(email="user@example.com", password="short123")


def test_private_rate_limit_identity_does_not_expose_email():
    identity = private_identity("User@Example.com")
    assert identity == private_identity("user@example.com")
    assert "user" not in identity
