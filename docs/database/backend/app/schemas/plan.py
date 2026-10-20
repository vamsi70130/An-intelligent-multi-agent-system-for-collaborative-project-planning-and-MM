import uuid
from datetime import datetime

from pydantic import BaseModel


class ModuleOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None

    class Config:
        from_attributes = True


class TaskOut(BaseModel):
    id: uuid.UUID
    code: str
    title: str
    description: str | None
    module_id: uuid.UUID | None
    priority: str
    estimated_effort_hours: float | None
    required_skills: list
    acceptance_criteria: list
    expected_artifact: str | None
    verification_method: str
    user_status: str
    evidence_status: str
    verification_status: str
    completion_percentage: int
    planned_start: datetime | None
    planned_end: datetime | None
    actual_start: datetime | None
    actual_end: datetime | None

    class Config:
        from_attributes = True


class DependencyOut(BaseModel):
    task_id: uuid.UUID
    depends_on_task_id: uuid.UUID


class AssignmentOut(BaseModel):
    task_id: uuid.UUID
    assignee_type: str
    assignee_label: str
    rationale: str | None

    class Config:
        from_attributes = True


class TechRecommendationOut(BaseModel):
    category: str
    technology: str
    reason: str | None
    advantages: list
    disadvantages: list
    compatibility_notes: str | None
    confidence: float | None

    class Config:
        from_attributes = True


class TimelineOut(BaseModel):
    kind: str
    start_date: datetime | None
    end_date: datetime | None
    milestones: list
    weekly_schedule: list
    critical_path: list

    class Config:
        from_attributes = True


class PlanGenerateResult(BaseModel):
    status: str
    errors: list[str] = []
    modules: list[ModuleOut] = []
    tasks: list[TaskOut] = []
    dependencies: list[DependencyOut] = []
    assignments: list[AssignmentOut] = []
    technology_recommendations: list[TechRecommendationOut] = []
    planned_timeline: TimelineOut | None = None
