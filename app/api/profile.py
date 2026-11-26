import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.database import SessionLocal
from app.core.security import get_optional_user, require_user
from app.models.user import User

router = APIRouter(prefix="/profile", tags=["Profile"])


class ProfileUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    education: str | None = None
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None


def _profile(user: User | None) -> dict:
    if user is None:
        return {"authenticated": False, "profile": None}
    links = {}
    try:
        links = json.loads(user.links or "{}")
    except (TypeError, ValueError):
        pass
    return {
        "authenticated": True,
        "profile": {
            "name": user.name, "email": user.email, "phone": user.phone or "",
            "education": user.education or "", "linkedin": links.get("linkedin", ""),
            "github": links.get("github", ""), "portfolio": links.get("portfolio", ""),
        },
    }


@router.get("")
def get_profile(user: User | None = Depends(get_optional_user)):
    return _profile(user)


@router.put("")
def update_profile(payload: ProfileUpdate, user: User | None = Depends(get_optional_user)):
    user = require_user(user)
    db = SessionLocal()
    try:
        saved = db.query(User).filter(User.id == user.id).first()
        values = payload.dict(exclude_unset=True)
        if "name" in values and values["name"]:
            saved.name = values["name"].strip()
        if "phone" in values:
            saved.phone = values["phone"]
        if "education" in values:
            saved.education = values["education"]
        links = {}
        try:
            links = json.loads(saved.links or "{}")
        except (ValueError, TypeError):
            pass
        for key in ("linkedin", "github", "portfolio"):
            if key in values:
                links[key] = values[key]
        saved.links = json.dumps(links)
        db.commit()
        db.refresh(saved)
        return _profile(saved)
    finally:
        db.close()
