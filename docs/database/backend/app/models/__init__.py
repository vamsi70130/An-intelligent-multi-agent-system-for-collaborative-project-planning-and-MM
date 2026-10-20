"""Import every model so Base.metadata is fully populated for Alembic
autogenerate and for create_all() in tests."""
from app.models.user import User  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.requirement import Requirement, ResearchItem  # noqa: F401
from app.models.task import Module, Task, TaskDependency, Assignment  # noqa: F401
from app.models.planning import (  # noqa: F401
    TechnologyRecommendation,
    Timeline,
    TimelineVersion,
    ProgressHistory,
)
from app.models.development import (  # noqa: F401
    Evidence,
    VerificationResult,
    Conflict,
    AgentLog,
    GeneratedFile,
    TestResult,
    Bug,
    ApprovalRequest,
)
