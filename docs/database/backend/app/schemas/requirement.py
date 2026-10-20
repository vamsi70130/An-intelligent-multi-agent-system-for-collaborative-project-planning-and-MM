import uuid
from datetime import datetime

from pydantic import BaseModel


class RequirementOut(BaseModel):
    id: uuid.UUID
    kind: str
    ref_code: str | None
    text: str
    priority: str | None
    category: str | None
    is_assumption: bool
    risk: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class RequirementGenerateResult(BaseModel):
    status: str  # success | not_configured | failed
    errors: list[str] = []
    project_summary: str | None = None
    requirements: list[RequirementOut] = []
    clarification_questions: list[str] = []
