import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.core.security import hash_password, issue_token, verify_password
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


class Credentials(BaseModel):
    name: str | None = None
    email: str
    password: str


def _user_payload(user: User, token: str) -> dict:
    return {
        "access_token": token, "token_type": "bearer",
        "user": {"id": user.id, "name": user.name, "email": user.email},
    }


@router.post("/register")
def register(payload: Credentials):
    email = payload.email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    if len(payload.password) < 8:
        raise HTTPException(status_code=422, detail="Password must contain at least 8 characters.")
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name is required to create an account.")

    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        user = User(name=name, email=email, password_hash=hash_password(payload.password))
        db.add(user)
        db.commit()
        db.refresh(user)
        return _user_payload(user, issue_token(user.id))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    finally:
        db.close()


@router.post("/login")
def login(payload: Credentials):
    email = payload.email.strip().lower()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Email or password is incorrect.")
        return _user_payload(user, issue_token(user.id))
    finally:
        db.close()
