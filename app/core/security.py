import hashlib
import hmac
import os
import secrets
import time

from fastapi import Header, HTTPException
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.user import User

TOKEN_TTL_SECONDS = 60 * 60 * 12
PBKDF2_ROUNDS = 310_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, rounds, salt_hex, expected_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds)
        ).hex()
        return hmac.compare_digest(actual, expected_hex)
    except (ValueError, TypeError):
        return False


def _secret() -> bytes:
    return os.getenv("SKILLPATH_SECRET_KEY", "skillpath-local-demo-change-this").encode()


def issue_token(user_id: int) -> str:
    expires = int(time.time()) + TOKEN_TTL_SECONDS
    payload = f"{user_id}.{expires}"
    signature = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def token_user_id(token: str) -> int:
    try:
        user_text, expires_text, signature = token.split(".", 2)
        payload = f"{user_text}.{expires_text}"
        expected = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected) or int(expires_text) < int(time.time()):
            raise ValueError
        return int(user_text)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Session is invalid or expired.")


def get_optional_user(authorization: str | None = Header(default=None)) -> User | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Use a valid Bearer access token.")
    user_id = token_user_id(token)
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise HTTPException(status_code=401, detail="Account no longer exists.")
        return user
    finally:
        db.close()


def require_user(user: User | None) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Log in to use this feature.")
    return user
