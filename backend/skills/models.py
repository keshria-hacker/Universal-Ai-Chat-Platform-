"""
skills/models.py — SQLAlchemy tables for skill execution history and user
preferences. Kept separate from backend/models.py so the skills subsystem
can evolve independently.
"""
import uuid
from datetime import UTC, datetime

from database import Base
from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column


def nid() -> str:
    return uuid.uuid4().hex[:12]


class SkillExecution(Base):
    __tablename__ = "skill_executions"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=nid)
    skill_id: Mapped[str] = mapped_column(String(64), index=True)
    skill_name: Mapped[str] = mapped_column(String(128))
    params: Mapped[dict] = mapped_column(JSON, default={})
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    invocation_type: Mapped[str] = mapped_column(String(16))
    duration_ms: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC))


class UserSkillPreference(Base):
    __tablename__ = "user_skill_preferences"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=nid)
    skill_id: Mapped[str] = mapped_column(String(64), index=True)
    enabled: Mapped[bool] = mapped_column(default=True)
    auto_invoke: Mapped[bool] = mapped_column(default=False)
    custom_params: Mapped[dict] = mapped_column(JSON, default={})
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
