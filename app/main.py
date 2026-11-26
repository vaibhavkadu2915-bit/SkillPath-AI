from fastapi import FastAPI
from app.core.database import engine, Base
from app.models.user import User 
from app.models.certificate import Certificate
from app.models.user_skill import UserSkill
from app.models.resume import Resume
from app.core.database import migrate_legacy_schema
from app.api.skills import router as skills_router
from app.api.certificate import router as certificate_router
from app.api.auth import router as auth_router
from app.api.profile import router as profile_router
from app.api.resume import router as resume_router
from app.api.jobs import router as jobs_router
from app.api.skill_gap import router as skill_gap_router


Base.metadata.create_all(bind=engine)
migrate_legacy_schema()

app = FastAPI(
    title="SkillPath AI",
    description="Certificate-Based Skill Extraction, ATS Resume and Career Guidance",
    version="1.0.0"
)

app.include_router(certificate_router)
app.include_router(skills_router)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(resume_router)
app.include_router(jobs_router)
app.include_router(skill_gap_router)

@app.get("/")
def home():
    return {
        "message": "Welcome to SkillPath AI",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }
