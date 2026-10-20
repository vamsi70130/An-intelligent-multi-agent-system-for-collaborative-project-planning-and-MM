import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.db import get_db
from app.core.deps import get_current_user, get_owned_project
from app.models.user import User
from app.models.project import Project
from app.models.task import Task
from app.models.development import AgentLog
from app.schemas.project import ProjectCreate, ProjectOut, ProjectStateOut

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = Project(
        owner_id=current_user.id,
        name=payload.name,
        description=payload.description,
        problem_statement=payload.problem_statement,
        goals=payload.goals,
        constraints_text=payload.constraints_text,
        team_members=json.dumps(payload.team_members),
        available_technologies=json.dumps(payload.available_technologies),
        duration_weeks=payload.duration_weeks,
        start_date=payload.start_date,
        current_stage="PROJECT_CREATED",
        health_status="NOT_STARTED",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return ProjectOut.model_validate(project)


@router.get("", response_model=list[ProjectOut])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    projects = (
        db.query(Project)
        .filter(Project.owner_id == current_user.id)
        .order_by(Project.created_at.desc())
        .all()
    )
    return [ProjectOut.model_validate(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project: Project = Depends(get_owned_project)):
    return ProjectOut.model_validate(project)


@router.get("/{project_id}/state", response_model=ProjectStateOut)
def get_project_state(
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    counts_query = (
        db.query(Task.user_status, func.count(Task.id))
        .filter(Task.project_id == project.id)
        .group_by(Task.user_status)
        .all()
    )
    task_counts = {status: count for status, count in counts_query}

    recent_logs = (
        db.query(AgentLog)
        .filter(AgentLog.project_id == project.id)
        .order_by(AgentLog.created_at.desc())
        .limit(10)
        .all()
    )
    latest_agent_runs = [
        {
            "agent_name": log.agent_name,
            "status": log.status,
            "created_at": log.created_at.isoformat() if log.created_at else None,
            "error_message": log.error_message,
        }
        for log in recent_logs
    ]

    return ProjectStateOut(
        project_id=project.id,
        current_stage=project.current_stage,
        health_status=project.health_status,
        task_counts=task_counts,
        latest_agent_runs=latest_agent_runs,
    )


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    db.delete(project)
    db.commit()
    return None
