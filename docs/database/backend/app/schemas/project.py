import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    problem_statement: str = ""
    goals: str = ""
    constraints_text: str = ""
    team_members: list[str] = []
    available_technologies: list[str] = []
    duration_weeks: int = 4
    start_date: datetime | None = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    problem_statement: str
    goals: str
    constraints_text: str
    duration_weeks: int
    start_date: datetime | None
    current_stage: str
    health_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectStateOut(BaseModel):
    project_id: uuid.UUID
    current_stage: str
    health_status: str
    task_counts: dict
    latest_agent_runs: list[dict]
