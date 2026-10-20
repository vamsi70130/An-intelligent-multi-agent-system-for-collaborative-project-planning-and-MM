import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Text, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.db import Base


USER_STATUS_VALUES = ["NOT_STARTED", "IN_PROGRESS", "SUBMITTED_FOR_VERIFICATION", "COMPLETED"]
VERIFICATION_STATUS_VALUES = ["NOT_APPLICABLE", "PENDING", "VERIFIED", "FAILED", "HUMAN_REVIEW"]
EVIDENCE_STATUS_VALUES = ["NONE", "PARTIAL", "SUBMITTED"]


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    project = relationship("Project", back_populates="modules")
    tasks = relationship("Task", back_populates="module", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    module_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("modules.id"), nullable=True)

    code: Mapped[str] = mapped_column(String(30), nullable=False)  # TASK-001
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    estimated_effort_hours: Mapped[float] = mapped_column(Numeric(6, 2), nullable=True)
    required_skills: Mapped[list] = mapped_column(JSONB, default=list)
    acceptance_criteria: Mapped[list] = mapped_column(JSONB, default=list)
    expected_artifact: Mapped[str] = mapped_column(String(500), nullable=True)
    verification_method: Mapped[str] = mapped_column(String(50), default="manual_review")

    # -- lifecycle (Section 8 / Step 13-14 of spec) --
    user_status: Mapped[str] = mapped_column(String(40), default="NOT_STARTED", nullable=False)
    evidence_status: Mapped[str] = mapped_column(String(20), default="NONE", nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), default="NOT_APPLICABLE", nullable=False)
    completion_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    repair_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # -- timing: planned vs actual --
    planned_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    planned_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="tasks")
    module = relationship("Module", back_populates="tasks")
    assignments = relationship("Assignment", back_populates="task", cascade="all, delete-orphan")
    dependencies = relationship(
        "TaskDependency", foreign_keys="TaskDependency.task_id",
        back_populates="task", cascade="all, delete-orphan",
    )
    progress_history = relationship("ProgressHistory", back_populates="task", cascade="all, delete-orphan")
    evidence_items = relationship("Evidence", back_populates="task", cascade="all, delete-orphan")
    verification_results = relationship("VerificationResult", back_populates="task", cascade="all, delete-orphan")
    test_results = relationship("TestResult", back_populates="task", cascade="all, delete-orphan")
    bugs = relationship("Bug", back_populates="task", cascade="all, delete-orphan")
    generated_files = relationship("GeneratedFile", back_populates="task", cascade="all, delete-orphan")


class TaskDependency(Base):
    __tablename__ = "task_dependencies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    depends_on_task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)

    task = relationship("Task", foreign_keys=[task_id], back_populates="dependencies")
    depends_on = relationship("Task", foreign_keys=[depends_on_task_id])


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    assignee_type: Mapped[str] = mapped_column(String(20), nullable=False)  # human|ai|human_ai
    assignee_label: Mapped[str] = mapped_column(String(255), nullable=False)  # name or agent name
    rationale: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task = relationship("Task", back_populates="assignments")
