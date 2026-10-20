import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import Base


PROJECT_STAGES = [
    "PROJECT_CREATED",
    "REQUIREMENTS_ANALYSIS",
    "RESEARCH",
    "PLANNING",
    "TECHNOLOGY_SELECTION",
    "TASK_GENERATION",
    "DEPENDENCY_ANALYSIS",
    "TASK_ALLOCATION",
    "TIMELINE_GENERATION",
    "READY_FOR_DEVELOPMENT",
    "DEVELOPMENT",
    "TESTING",
    "REVIEW",
    "VERIFICATION",
    "COMPLETED",
    "HUMAN_INTERVENTION_REQUIRED",
]


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True, default="")
    problem_statement: Mapped[str] = mapped_column(Text, nullable=True, default="")
    goals: Mapped[str] = mapped_column(Text, nullable=True, default="")
    constraints_text: Mapped[str] = mapped_column(Text, nullable=True, default="")
    team_members: Mapped[str] = mapped_column(Text, nullable=True, default="")  # JSON-encoded list
    available_technologies: Mapped[str] = mapped_column(Text, nullable=True, default="")
    duration_weeks: Mapped[int] = mapped_column(default=4, nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    current_stage: Mapped[str] = mapped_column(String(50), default="PROJECT_CREATED", nullable=False)
    health_status: Mapped[str] = mapped_column(String(30), default="NOT_STARTED", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="projects")
    requirements = relationship("Requirement", back_populates="project", cascade="all, delete-orphan")
    modules = relationship("Module", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    tech_recommendations = relationship("TechnologyRecommendation", back_populates="project", cascade="all, delete-orphan")
    timelines = relationship("Timeline", back_populates="project", cascade="all, delete-orphan")
    conflicts = relationship("Conflict", back_populates="project", cascade="all, delete-orphan")
    agent_logs = relationship("AgentLog", back_populates="project", cascade="all, delete-orphan")
    research_items = relationship("ResearchItem", back_populates="project", cascade="all, delete-orphan")
