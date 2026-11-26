import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.certificate import extract_certificate_text
from app.core.database import SessionLocal
from app.core.security import get_optional_user
from app.models.certificate import Certificate
from app.models.user import User
from app.models.user_skill import UserSkill
from app.services.skill_extractor import normalize_skill_name

router = APIRouter(prefix="/skills", tags=["Skill Profile"])


class SkillConfirmation(BaseModel):
    skills: list[str] = Field(default_factory=list)
    certificate_id: int | None = None


@router.post("/extract/{filename}")
def extract_certificate_skills(filename: str, user: User | None = Depends(get_optional_user)):
    result = extract_certificate_text(filename, user)
    return {
        "message": "Certificate skills extracted and saved. Review and confirm them before use.",
        "filename": filename, "certificate_id": result["certificate_id"],
        "status": "processed", "extraction_method": result["extraction_method"],
        "character_count": result["character_count"], "needs_ocr": result["needs_ocr"],
        "metadata": result["metadata"], "skill_count": result["skill_count"],
        "skills": result["skills"],
    }


@router.get("/extracted")
def get_extracted_skills(user: User | None = Depends(get_optional_user)):
    db = SessionLocal()
    try:
        query = db.query(Certificate)
        skills_query = db.query(UserSkill)
        if user is not None:
            query = query.filter((Certificate.user_id == user.id) | (Certificate.user_id.is_(None)))
            skills_query = skills_query.filter(UserSkill.user_id == user.id)
        else:
            skills_query = skills_query.filter(UserSkill.user_id.is_(None))
        records = query.order_by(Certificate.id.desc()).all()
        confirmed = sorted({row.canonical_name for row in skills_query.filter(UserSkill.confirmed.is_(True)).all()})
        certificates = []
        for record in records:
            try:
                detected = json.loads(record.detected_skills or "[]")
            except (ValueError, TypeError):
                detected = []
            certificates.append({
                "certificate_id": record.id, "filename": record.original_filename,
                "title": record.title or "", "status": record.status or "uploaded",
                "skills": detected,
            })
        return {"certificates": certificates, "confirmed_skills": confirmed}
    finally:
        db.close()


@router.post("/confirm")
def confirm_skills(payload: SkillConfirmation, user: User | None = Depends(get_optional_user)):
    if len(payload.skills) > 100:
        raise HTTPException(status_code=422, detail="Confirm no more than 100 skills at once.")
    normalized = sorted({normalize_skill_name(value) for value in payload.skills if value.strip()})
    if any(len(value) > 80 for value in normalized):
        raise HTTPException(status_code=422, detail="Skill names must be 80 characters or fewer.")
    db = SessionLocal()
    try:
        certificate_id = payload.certificate_id
        if certificate_id is not None:
            certificate = db.query(Certificate).filter(Certificate.id == certificate_id).first()
            if certificate is None or (user and certificate.user_id not in (None, user.id)):
                raise HTTPException(status_code=404, detail="Certificate not found.")
        user_id = user.id if user else None
        query = db.query(UserSkill).filter(UserSkill.user_id == user_id)
        query.delete(synchronize_session=False)
        for name in normalized:
            db.add(UserSkill(
                user_id=user_id, canonical_name=name, confirmed=True,
                source_certificate_id=certificate_id,
            ))
        db.commit()
        return {"message": "Confirmed skills saved to your profile.", "confirmed_skills": normalized}
    except HTTPException:
        db.rollback()
        raise
    finally:
        db.close()
