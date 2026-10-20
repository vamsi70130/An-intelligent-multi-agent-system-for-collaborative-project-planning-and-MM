import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_owned_project
from app.models.project import Project
from app.models.task import Module, Task, TaskDependency
from app.models.planning import Timeline
from app.schemas.plan import ModuleOut, TaskOut, DependencyOut, TimelineOut

router = APIRouter(tags=["planning-readonly"])


@router.get("/api/modules/projects/{project_id}", response_model=list[ModuleOut])
def list_modules(project: Project = Depends(get_owned_project), db: Session = Depends(get_db)):
    modules = db.query(Module).filter(Module.project_id == project.id).all()
    return [ModuleOut.model_validate(m) for m in modules]


@router.get("/api/tasks/projects/{project_id}", response_model=list[TaskOut])
def list_tasks(project: Project = Depends(get_owned_project), db: Session = Depends(get_db)):
    tasks = db.query(Task).filter(Task.project_id == project.id).order_by(Task.code).all()
    return [TaskOut.model_validate(t) for t in tasks]


@router.get("/api/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: uuid.UUID, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskOut.model_validate(task)


@router.get("/api/dependencies/projects/{project_id}", response_model=list[DependencyOut])
def list_dependencies(project: Project = Depends(get_owned_project), db: Session = Depends(get_db)):
    task_ids = [t.id for t in db.query(Task.id).filter(Task.project_id == project.id).all()]
    deps = db.query(TaskDependency).filter(TaskDependency.task_id.in_(task_ids)).all()
    return [DependencyOut(task_id=d.task_id, depends_on_task_id=d.depends_on_task_id) for d in deps]


@router.get("/api/timeline/projects/{project_id}", response_model=TimelineOut)
def get_timeline(
    kind: str = "current",
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    if kind not in ("planned", "current"):
        raise HTTPException(status_code=400, detail="kind must be 'planned' or 'current'")
    timeline = (
        db.query(Timeline)
        .filter(Timeline.project_id == project.id, Timeline.kind == kind)
        .first()
    )
    if not timeline:
        raise HTTPException(status_code=404, detail=f"No '{kind}' timeline exists yet for this project")
    return TimelineOut.model_validate(timeline)
