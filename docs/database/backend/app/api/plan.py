import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_owned_project
from app.models.project import Project
from app.models.requirement import Requirement, ResearchItem
from app.models.task import Module, Task, TaskDependency, Assignment
from app.models.planning import TechnologyRecommendation, Timeline
from app.agents.base import run_agent
from app.agents.research_agent import research_project
from app.agents.decomposition_agent import decompose_project
from app.agents.technology_agent import recommend_technologies
from app.agents.allocation_agent import allocate_tasks
from app.agents.timeline_agent import generate_timeline, CircularDependencyError
from app.schemas.plan import (
    PlanGenerateResult, ModuleOut, TaskOut, DependencyOut, AssignmentOut,
    TechRecommendationOut, TimelineOut,
)

router = APIRouter(prefix="/api/plan", tags=["plan"])


@router.post("/projects/{project_id}/generate", response_model=PlanGenerateResult)
def generate_plan(
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    existing_planned = (
        db.query(Timeline)
        .filter(Timeline.project_id == project.id, Timeline.kind == "planned")
        .first()
    )
    if existing_planned:
        raise HTTPException(
            status_code=409,
            detail=(
                "This project already has a planned timeline. The original plan is "
                "immutable -- use the adaptive replanning endpoint instead of "
                "regenerating the plan from scratch."
            ),
        )

    functional_reqs = (
        db.query(Requirement)
        .filter(Requirement.project_id == project.id, Requirement.kind == "functional")
        .all()
    )
    fr_texts = [r.text for r in functional_reqs]
    if not fr_texts:
        raise HTTPException(
            status_code=400,
            detail="Generate requirements first (POST /api/requirements/projects/{id}/generate).",
        )

    # ---- 1. Research Agent ----
    research_result = run_agent(
        db, project.id, "ResearchAgent",
        fn=lambda: research_project(project, fr_texts),
    )
    if research_result["status"] != "success":
        return PlanGenerateResult(status=research_result["status"], errors=research_result["errors"])
    research_output = research_result["output"]

    db.query(ResearchItem).filter(ResearchItem.project_id == project.id).delete()
    research_items = []
    for tech in research_output.get("relevant_technologies", []):
        research_items.append(ResearchItem(project_id=project.id, kind="technology", title=tech))
    for algo in research_output.get("algorithms_or_methods", []):
        research_items.append(ResearchItem(
            project_id=project.id, kind="algorithm", title=algo.get("name", ""),
            summary=algo.get("use_case"),
        ))
    for approach in research_output.get("existing_approaches", []):
        research_items.append(ResearchItem(
            project_id=project.id, kind="existing_approach", title=approach.get("name", ""),
            summary=approach.get("summary"),
        ))
    for gap in research_output.get("research_gaps", []):
        research_items.append(ResearchItem(project_id=project.id, kind="research_gap", title=gap))
    for ref in research_output.get("references", []):
        research_items.append(ResearchItem(
            project_id=project.id, kind="reference", title=ref.get("title", ""),
            summary=ref.get("note"), is_ai_generated=True,
        ))
    db.add_all(research_items)

    research_summary = "; ".join(research_output.get("relevant_technologies", []))

    # ---- 2. Decomposition Agent ----
    decomp_result = run_agent(
        db, project.id, "ProjectDecompositionAgent",
        fn=lambda: decompose_project(project, fr_texts, research_summary),
    )
    if decomp_result["status"] != "success":
        db.commit()  # keep research even if decomposition fails
        return PlanGenerateResult(status=decomp_result["status"], errors=decomp_result["errors"])
    decomp_output = decomp_result["output"]

    module_ref_to_id: dict[str, uuid.UUID] = {}
    created_modules = []
    for m in decomp_output.get("modules", []):
        module = Module(project_id=project.id, name=m.get("name", ""), description=m.get("description"))
        db.add(module)
        db.flush()  # get module.id without committing
        module_ref_to_id[m["module_ref"]] = module.id
        created_modules.append(module)

    task_ref_to_id: dict[str, uuid.UUID] = {}
    created_tasks = []
    task_defs = decomp_output.get("tasks", [])
    for idx, t in enumerate(task_defs, start=1):
        task = Task(
            project_id=project.id,
            module_id=module_ref_to_id.get(t.get("module_ref")),
            code=f"TASK-{idx:03d}",
            title=t.get("title", ""),
            description=t.get("description"),
            priority=t.get("priority", "medium"),
            estimated_effort_hours=t.get("estimated_effort_hours"),
            required_skills=t.get("required_skills", []),
            acceptance_criteria=t.get("acceptance_criteria", []),
            expected_artifact=t.get("expected_artifact"),
            verification_method=t.get("verification_method", "manual_review"),
        )
        db.add(task)
        db.flush()
        task_ref_to_id[t["task_ref"]] = task.id
        created_tasks.append((task, t.get("depends_on_refs", [])))

    created_dependencies = []
    for task, depends_on_refs in created_tasks:
        for ref in depends_on_refs:
            depends_on_id = task_ref_to_id.get(ref)
            if depends_on_id and depends_on_id != task.id:
                dep = TaskDependency(task_id=task.id, depends_on_task_id=depends_on_id)
                db.add(dep)
                created_dependencies.append(dep)

    db.flush()

    # ---- 3. Technology Agent ----
    tech_result = run_agent(
        db, project.id, "TechnologyAgent",
        fn=lambda: recommend_technologies(project, fr_texts),
    )
    created_tech = []
    if tech_result["status"] == "success":
        db.query(TechnologyRecommendation).filter(TechnologyRecommendation.project_id == project.id).delete()
        for rec in tech_result["output"].get("recommendations", []):
            tr = TechnologyRecommendation(
                project_id=project.id,
                category=rec.get("category", "other"),
                technology=rec.get("technology", ""),
                reason=rec.get("reason"),
                advantages=rec.get("advantages", []),
                disadvantages=rec.get("disadvantages", []),
                compatibility_notes=rec.get("compatibility_notes"),
                confidence=rec.get("confidence"),
            )
            db.add(tr)
            created_tech.append(tr)

    # ---- 4. Task Allocation Agent (deterministic) ----
    team_members = json.loads(project.team_members or "[]")
    task_dicts_for_alloc = [
        {"task_id": str(task.id), "required_skills": task.required_skills, "priority": task.priority}
        for task, _ in created_tasks
    ]
    allocation_output = allocate_tasks(task_dicts_for_alloc, team_members)
    run_agent(
        db, project.id, "TaskAllocationAgent",
        fn=lambda: {"assignments": allocation_output},
    )
    created_assignments = []
    for a in allocation_output:
        assignment = Assignment(
            task_id=uuid.UUID(a["task_id"]),
            assignee_type=a["assignee_type"],
            assignee_label=a["assignee_label"],
            rationale=a["rationale"],
        )
        db.add(assignment)
        created_assignments.append(assignment)

    # ---- 5. Timeline Agent (deterministic) ----
    task_dicts_for_timeline = [
        {"task_id": str(task.id), "estimated_effort_hours": task.estimated_effort_hours, "title": task.title}
        for task, _ in created_tasks
    ]
    dep_pairs = [(str(dep.task_id), str(dep.depends_on_task_id)) for dep in created_dependencies]

    try:
        timeline_output = generate_timeline(
            task_dicts_for_timeline, dep_pairs, project.start_date, project.duration_weeks,
        )
    except CircularDependencyError as e:
        db.rollback()
        return PlanGenerateResult(status="failed", errors=[str(e)])

    run_agent(db, project.id, "TimelineManagerAgent", fn=lambda: timeline_output)

    # assign planned_start/planned_end per task from the weekly schedule (best-effort)
    task_by_id = {str(task.id): task for task, _ in created_tasks}
    from datetime import timedelta
    if project.start_date:
        for week in timeline_output["weekly_schedule"]:
            week_start = project.start_date + timedelta(weeks=week["week"] - 1)
            week_end = week_start + timedelta(weeks=1)
            for tid in week["task_ids"]:
                t = task_by_id.get(tid)
                if t:
                    t.planned_start = week_start
                    t.planned_end = week_end

    planned_timeline = Timeline(
        project_id=project.id,
        kind="planned",
        start_date=project.start_date,
        end_date=None,
        milestones=timeline_output["milestones"],
        weekly_schedule=timeline_output["weekly_schedule"],
        critical_path=timeline_output["critical_path"],
    )
    current_timeline = Timeline(
        project_id=project.id,
        kind="current",
        start_date=project.start_date,
        end_date=None,
        milestones=timeline_output["milestones"],
        weekly_schedule=timeline_output["weekly_schedule"],
        critical_path=timeline_output["critical_path"],
    )
    db.add(planned_timeline)
    db.add(current_timeline)

    project.current_stage = "READY_FOR_DEVELOPMENT"
    project.health_status = "ON_TRACK"
    db.add(project)

    db.commit()

    for m in created_modules:
        db.refresh(m)
    for task, _ in created_tasks:
        db.refresh(task)
    for a in created_assignments:
        db.refresh(a)
    for tr in created_tech:
        db.refresh(tr)
    db.refresh(planned_timeline)

    return PlanGenerateResult(
        status="success",
        modules=[ModuleOut.model_validate(m) for m in created_modules],
        tasks=[TaskOut.model_validate(t) for t, _ in created_tasks],
        dependencies=[
            DependencyOut(task_id=d.task_id, depends_on_task_id=d.depends_on_task_id)
            for d in created_dependencies
        ],
        assignments=[AssignmentOut.model_validate(a) for a in created_assignments],
        technology_recommendations=[TechRecommendationOut.model_validate(t) for t in created_tech],
        planned_timeline=TimelineOut.model_validate(planned_timeline),
    )
