from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from app.core.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    version = Column(Integer, nullable=False, default=1)
    docx_path = Column(String, nullable=False)
    pdf_path = Column(String, nullable=False)
    ats_score = Column(Float, nullable=True)
    resume_text = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
