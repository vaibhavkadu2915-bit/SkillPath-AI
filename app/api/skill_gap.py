from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import get_optional_user
from app.models.user import User
from app.models.user_skill import UserSkill
from app.services.career_service import analyze_gap

router = APIRouter(prefix="/skill-gap", tags=["Career Guidance"])


@router.get("")
def get_skill_gap(
    role_id: str = Query(...),
    skills: list[str] | None = Query(default=None),
    user: User | None = Depends(get_optional_user),
):
    db: Session = SessionLocal()
    try:
        if user is not None:
            rows = db.query(UserSkill).filter(
                UserSkill.user_id == user.id, UserSkill.confirmed.is_(True)
            ).all()
            owned = [row.canonical_name for row in rows]
        else:
            owned = skills or []
        result = analyze_gap(owned, role_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Unknown role. See GET /jobs/roles for available roles.")
        return result
    finally:
        db.close()
