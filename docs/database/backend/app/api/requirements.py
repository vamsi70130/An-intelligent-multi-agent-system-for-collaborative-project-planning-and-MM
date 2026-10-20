from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_owned_project
from app.models.project import Project
from app.models.requirement import Requirement
from app.agents.base import run_agent
from app.agents.requirement_agent import analyze_requirements
from app.schemas.requirement import RequirementOut, RequirementGenerateResult

router = APIRouter(prefix="/api/requirements", tags=["requirements"])


@router.post("/projects/{project_id}/generate", response_model=RequirementGenerateResult)
def generate_requirements(
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    result = run_agent(
        db=db,
        project_id=project.id,
        agent_name="RequirementAnalysisAgent",
        fn=lambda: analyze_requirements(project),
        input_snapshot={
            "description": project.description,
            "problem_statement": project.problem_statement,
            "goals": project.goals,
        },
    )

    if result["status"] != "success":
        return RequirementGenerateResult(status=result["status"], errors=result["errors"])

    output = result["output"]

    # Persist -- replace prior AI-generated requirements for this project
    # (idempotent regeneration) but never fabricate anything not returned
    # by the LLM.
    db.query(Requirement).filter(Requirement.project_id == project.id).delete()

    created: list[Requirement] = []
    for fr in output.get("functional_requirements", []):
        created.append(Requirement(
            project_id=project.id, kind="functional", ref_code=fr.get("ref_code"),
            text=fr.get("text", ""), priority=fr.get("priority"),
        ))
    for nfr in output.get("non_functional_requirements", []):
        created.append(Requirement(
            project_id=project.id, kind="non_functional", ref_code=nfr.get("ref_code"),
            text=nfr.get("text", ""), category=nfr.get("category"),
        ))
    for role in output.get("user_roles", []):
        created.append(Requirement(
            project_id=project.id, kind="user_role",
            text=f"{role.get('role', '')}: {role.get('description', '')}",
        ))
    for c in output.get("constraints", []):
        created.append(Requirement(project_id=project.id, kind="constraint", text=c))
    for a in output.get("assumptions", []):
        created.append(Requirement(
            project_id=project.id, kind="assumption", text=a.get("text", ""),
            is_assumption=True, risk=a.get("risk"),
        ))
    for ac in output.get("acceptance_criteria", []):
        created.append(Requirement(project_id=project.id, kind="acceptance_criteria", text=ac))

    db.add_all(created)

    project.current_stage = "REQUIREMENTS_ANALYSIS"
    db.add(project)
    db.commit()
    for r in created:
        db.refresh(r)

    return RequirementGenerateResult(
        status="success",
        project_summary=output.get("project_summary"),
        requirements=[RequirementOut.model_validate(r) for r in created],
        clarification_questions=output.get("clarification_questions", []),
    )


@router.get("/projects/{project_id}", response_model=list[RequirementOut])
def list_requirements(
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    reqs = db.query(Requirement).filter(Requirement.project_id == project.id).all()
    return [RequirementOut.model_validate(r) for r in reqs]
