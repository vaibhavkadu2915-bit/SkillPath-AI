import json
from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.core.database import SessionLocal
from app.core.security import get_optional_user
from app.core.settings import GENERATED_DIR
from app.models.resume import Resume
from app.models.certificate import Certificate
from app.models.user import User
from app.models.user_skill import UserSkill
from app.services.ats_checker import check_ats
from app.services.resume_builder import generate_resume_files

router = APIRouter(prefix="/resume", tags=["Resume"])


class ResumeRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    education: str | None = None
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None
    summary: str | None = None
    projects: str | None = None
    experience: str | None = None
    certifications: str | None = None
    skills: list[str] = Field(default_factory=list)


class ATSRequest(BaseModel):
    resume_text: str = ""
    job_description: str = ""
    keywords: list[str] = Field(default_factory=list)


def _profile_from_user(user: User, request: ResumeRequest) -> dict:
    links = {}
    try:
        links = json.loads(user.links or "{}")
    except (TypeError, ValueError):
        pass
    profile = {
        "name": user.name, "email": user.email, "phone": user.phone or "",
        "education": user.education or "", "linkedin": links.get("linkedin", ""),
        "github": links.get("github", ""), "portfolio": links.get("portfolio", ""),
    }
    for key in ("name", "email", "phone", "education", "linkedin", "github", "portfolio", "summary", "projects", "experience", "certifications"):
        value = getattr(request, key, None)
        if value:
            profile[key] = value.strip()
    return profile


@router.post("/generate")
def generate_resume(payload: ResumeRequest, user: User | None = Depends(get_optional_user)):
    db = SessionLocal()
    docx_path = pdf_path = None
    try:
        if user is not None:
            saved_user = db.query(User).filter(User.id == user.id).first()
            profile = _profile_from_user(saved_user, payload)
            user_id = user.id
        else:
            profile = payload.dict(exclude={"skills"})
            user_id = None
        rows = db.query(UserSkill).filter(
            UserSkill.user_id == user_id, UserSkill.confirmed.is_(True)
        ).all()
        skills = {row.canonical_name for row in rows}
        if user is None:
            skills.update(skill.strip() for skill in payload.skills if skill.strip())
        skills = sorted(skills)

        certificate_query = db.query(Certificate).filter(Certificate.status == "processed")
        if user is not None:
            certificate_query = certificate_query.filter(
                (Certificate.user_id == user.id) | (Certificate.user_id.is_(None))
            )
        else:
            certificate_query = certificate_query.filter(Certificate.user_id.is_(None))
        certificate_lines = []
        for item in certificate_query.order_by(Certificate.id.desc()).all():
            label = item.title or item.original_filename
            if item.issuer:
                label += f" — {item.issuer}"
            if item.issue_date:
                label += f" ({item.issue_date})"
            certificate_lines.append(label)
        if certificate_lines:
            additional = (profile.get("certifications") or "").strip()
            profile["certifications"] = "\n".join(([additional] if additional else []) + certificate_lines)

        if not profile.get("name"):
            raise HTTPException(status_code=422, detail="Add your name to the profile before generating a resume.")
        folder = (GENERATED_DIR / str(user.id if user else "guest")).resolve()
        folder.mkdir(parents=True, exist_ok=True)
        nonce = uuid.uuid4().hex
        docx_path = folder / f"resume-{nonce}.docx"
        pdf_path = folder / f"resume-{nonce}.pdf"
        resume_text = generate_resume_files(profile, skills, docx_path, pdf_path)
        baseline_score = check_ats(resume_text)["score"]
        previous = db.query(Resume).filter(Resume.user_id == (user.id if user else None)).count()
        record = Resume(
            user_id=user.id if user else None, version=previous + 1,
            docx_path=str(docx_path), pdf_path=str(pdf_path), ats_score=baseline_score,
            resume_text=resume_text,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return {
            "resume_id": record.id, "version": record.version,
            "docx_download": f"/resume/{record.id}/download?format=docx",
            "pdf_download": f"/resume/{record.id}/download?format=pdf",
            "resume_text": resume_text, "ats_score": baseline_score,
            "skills_included": skills,
        }
    except HTTPException:
        db.rollback()
        if docx_path:
            docx_path.unlink(missing_ok=True)
        if pdf_path:
            pdf_path.unlink(missing_ok=True)
        raise
    except Exception:
        db.rollback()
        if docx_path:
            docx_path.unlink(missing_ok=True)
        if pdf_path:
            pdf_path.unlink(missing_ok=True)
        raise
    finally:
        db.close()


@router.get("")
def list_resumes(user: User | None = Depends(get_optional_user)):
    db = SessionLocal()
    try:
        query = db.query(Resume)
        if user is not None:
            query = query.filter(Resume.user_id == user.id)
        else:
            query = query.filter(Resume.user_id.is_(None))
        return {"resumes": [
            {"resume_id": item.id, "version": item.version, "ats_score": item.ats_score,
             "created_at": item.created_at.isoformat() if item.created_at else None}
            for item in query.order_by(Resume.id.desc()).all()
        ]}
    finally:
        db.close()


@router.get("/{resume_id}/download")
def download_resume(
    resume_id: int,
    format: str = Query(default="docx"),
    user: User | None = Depends(get_optional_user),
):
    db = SessionLocal()
    try:
        if format not in {"docx", "pdf"}:
            raise HTTPException(status_code=422, detail="Format must be docx or pdf.")
        record = db.query(Resume).filter(Resume.id == resume_id).first()
        if record is None or (user and record.user_id != user.id) or (user is None and record.user_id is not None):
            raise HTTPException(status_code=404, detail="Resume not found.")
        path = Path(record.docx_path if format == "docx" else record.pdf_path)
        if not path.is_file():
            raise HTTPException(status_code=404, detail="The generated file is no longer available.")
        media_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            if format == "docx" else "application/pdf"
        )
        return FileResponse(path, media_type=media_type, filename=f"skillpath-resume-{resume_id}.{format}")
    finally:
        db.close()


@router.post("/check-ats")
def check_resume_ats(payload: ATSRequest):
    if not payload.resume_text.strip():
        raise HTTPException(status_code=422, detail="Paste resume text or generate a resume first.")
    return check_ats(payload.resume_text, payload.job_description, payload.keywords)
