import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class GoogleSignupSession(Base):
    __tablename__ = "google_signup_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    google_id = Column(String, nullable=False, index=True)
    email = Column(String, nullable=False)
    name = Column(String, nullable=False)

    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )