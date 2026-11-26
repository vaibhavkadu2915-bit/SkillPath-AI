from sqlalchemy import Column, DateTime, Integer, String, Text, func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    education = Column(Text, nullable=True)
    links = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True, server_default=func.current_timestamp())
