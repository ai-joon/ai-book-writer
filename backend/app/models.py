"""Database models for sopher.ai"""

from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, LargeBinary, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Project(Base):
    """Project represents a book writing project"""

    __tablename__ = "projects"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(Text, nullable=False)
    settings = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    sessions = relationship("Session", back_populates="project", cascade="all, delete-orphan")


class Session(Base):
    """Session represents a writing session within a project"""

    __tablename__ = "sessions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(PGUUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    user_id = Column(Text, nullable=False)
    context = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="sessions")
    events = relationship("Event", back_populates="session", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="session", cascade="all, delete-orphan")
    costs = relationship("Cost", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_session_project_created", "project_id", "created_at"),)


class Event(Base):
    """Event represents an action or state change in the system"""

    __tablename__ = "events"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(PGUUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    type = Column(Text, nullable=False)  # outline_start, chapter_draft, edit, etc.
    payload = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("Session", back_populates="events")

    __table_args__ = (Index("idx_event_session_created", "session_id", "created_at"),)


class Artifact(Base):
    """Artifact represents generated content (outlines, chapters, etc.)"""

    __tablename__ = "artifacts"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(PGUUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    kind = Column(Text, nullable=False)  # outline, chapter, manuscript, etc.
    path = Column(Text)  # storage path if applicable
    meta = Column(JSONB, default={})
    blob = Column(LargeBinary)  # for small content, larger goes to object storage
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("Session", back_populates="artifacts")

    __table_args__ = (Index("idx_artifact_session_kind", "session_id", "kind"),)


class Cost(Base):
    """Cost tracks token usage and costs per agent/session"""

    __tablename__ = "costs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(PGUUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    agent = Column(Text, nullable=False)  # writer, editor, etc.
    model = Column(Text)  # claude-3-5-sonnet, gpt-4o, etc.
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    usd = Column(Numeric(10, 6), default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("Session", back_populates="costs")

    __table_args__ = (
        Index("idx_cost_session_created", "session_id", "created_at"),
        Index("idx_cost_agent", "agent"),
    )
