import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, Request


def hash_password(password):
    salt = secrets.token_hex(16)
    value = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000).hex()
    return f"pbkdf2_sha256$600000${salt}${value}"


def check_password(password, encoded):
    try:
        _, iterations, salt, expected = encoded.split("$")
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def token_for(user, secret):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": user.id,
            "role": user.data["role"],
            "iss": "commerce-identity",
            "aud": "commerce",
            "iat": now,
            "exp": now + timedelta(minutes=30),
        },
        secret,
        algorithm="HS256",
    )


def user(request: Request):
    value = request.headers.get("authorization", "")
    if not value.startswith("Bearer "):
        raise HTTPException(401, "Bearer token required", headers={"WWW-Authenticate": "Bearer"})
    try:
        return jwt.decode(
            value[7:],
            request.app.state.settings.jwt_secret,
            algorithms=["HS256"],
            audience="commerce",
            issuer="commerce-identity",
            options={"require": ["sub", "role", "exp", "iat", "iss", "aud"]},
        )
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token") from None


def admin(request: Request):
    claims = user(request)
    if claims["role"] != "admin":
        raise HTTPException(403, "Administrator role required")
    return claims


def internal(request: Request):
    value = request.headers.get("x-internal-key", "")
    if not hmac.compare_digest(value, request.app.state.settings.internal_secret):
        raise HTTPException(403, "Service authentication required")
