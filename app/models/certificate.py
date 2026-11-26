
from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey, func
from app.core.database import Base


class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    file_path = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)

    status = Column(String, default="uploaded")

    extracted_text = Column(Text, nullable=True)
    extraction_method = Column(String, nullable=True)
    detected_skills = Column(Text, nullable=True)
    title = Column(String, nullable=True)
    issuer = Column(String, nullable=True)
    issue_date = Column(String, nullable=True)
    cert_type = Column(String, nullable=True)
    credential_id = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=True, server_default=func.current_timestamp())
