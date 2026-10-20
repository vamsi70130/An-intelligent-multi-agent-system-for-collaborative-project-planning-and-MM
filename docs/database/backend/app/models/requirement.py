import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Text, ForeignKey, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import Base


class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)

    kind: Mapped[str] = mapped_column(String(30), nullable=False)  # functional | non_functional | acceptance_criteria | user_role | assumption
    ref_code: Mapped[str] = mapped_column(String(20), nullable=True)  # e.g. FR-1
    text: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=True)  # must|should|could
    category: Mapped[str] = mapped_column(String(50), nullable=True)  # for NFRs: performance/security/...
    is_assumption: Mapped[bool] = mapped_column(Boolean, default=False)
    risk: Mapped[str] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="requirements")


class ResearchItem(Base):
    __tablename__ = "research_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)

    kind: Mapped[str] = mapped_column(String(30), nullable=False)  # technology|algorithm|existing_approach|research_gap|reference
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=True)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=True)  # distinguishes AI suggestion vs verified reference

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="research_items")
