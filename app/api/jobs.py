from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import get_optional_user
from app.models.user_skill import UserSkill
from app.models.user import User
from app.services.career_service import ROLES, role_recommendations

router = APIRouter(prefix="/jobs", tags=["Career Guidance"])


def _skills(db: Session, user: User | None, requested: list[str] | None) -> list[str]:
    if user is None:
        return requested or []
    rows = db.query(UserSkill).filter(
        UserSkill.user_id == user.id, UserSkill.confirmed.is_(True)
    ).all()
    return [row.canonical_name for row in rows]


@router.get("/roles")
def list_roles():
    return {"roles": [
        {"role_id": role["id"], "title": role["title"], "must_have": role["must"], "good_to_have": role["good"]}
        for role in ROLES
    ], "data_source": "small curated prototype dataset; no live job listings"}


@router.get("/recommend")
def recommend_jobs(
    skills: list[str] | None = Query(default=None),
    limit: int = Query(default=8, ge=1, le=12),
    user: User | None = Depends(get_optional_user),
):
    db = SessionLocal()
    try:
        owned = _skills(db, user, skills)
        return {"recommendations": role_recommendations(owned, limit), "skills_used": owned,
                "data_source": "small curated prototype dataset; match scores are skill overlap only"}
    finally:
        db.close()
