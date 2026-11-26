from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from app.core.database import Base


class UserSkill(Base):
    __tablename__ = "user_skills"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    canonical_name = Column(String, nullable=False, index=True)
    confirmed = Column(Boolean, nullable=False, default=True)
    source_certificate_id = Column(
        Integer, ForeignKey("certificates.id"), nullable=True
    )
