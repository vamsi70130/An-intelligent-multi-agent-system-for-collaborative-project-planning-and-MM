"""
Timeline Manager Agent (spec Step 11 / Section 2.3 G).

Deterministic scheduling: topological sort of the task dependency
graph, longest-path (critical path) computation by estimated effort,
and greedy bucketing into weekly buckets. This is intentionally not
LLM-based -- schedule math should be reproducible and checkable.
"""
from collections import defaultdict, deque
from datetime import timedelta


class CircularDependencyError(Exception):
    pass


def topological_order(task_ids: list[str], edges: list[tuple[str, str]]) -> list[str]:
    """edges: list of (task_id, depends_on_task_id). Returns a valid
    execution order, raises CircularDependencyError if none exists."""
    indegree = {t: 0 for t in task_ids}
    dependents = defaultdict(list)  # depends_on -> [dependents]

    for task_id, depends_on in edges:
        indegree[task_id] += 1
        dependents[depends_on].append(task_id)

    queue = deque([t for t in task_ids if indegree[t] == 0])
    order = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for dep in dependents[node]:
            indegree[dep] -= 1
            if indegree[dep] == 0:
                queue.append(dep)

    if len(order) != len(task_ids):
        raise CircularDependencyError(
            "Circular dependency detected -- cannot produce a valid schedule."
        )
    return order


def compute_critical_path(
    task_ids: list[str],
    edges: list[tuple[str, str]],
    effort_by_task: dict[str, float],
) -> tuple[list[str], dict[str, float]]:
    """Longest path by cumulative effort hours through the dependency DAG.
    Returns (critical_path_task_ids, earliest_finish_by_task)."""
    order = topological_order(task_ids, edges)
    deps_of = defaultdict(list)
    for task_id, depends_on in edges:
        deps_of[task_id].append(depends_on)

    earliest_finish: dict[str, float] = {}
    predecessor: dict[str, str | None] = {}

    for task_id in order:
        effort = effort_by_task.get(task_id, 0) or 0
        preds = deps_of.get(task_id, [])
        if not preds:
            earliest_finish[task_id] = effort
            predecessor[task_id] = None
        else:
            best_pred = max(preds, key=lambda p: earliest_finish.get(p, 0))
            earliest_finish[task_id] = earliest_finish.get(best_pred, 0) + effort
            predecessor[task_id] = best_pred

    if not earliest_finish:
        return [], {}

    end_task = max(earliest_finish, key=lambda t: earliest_finish[t])
    path = []
    cur: str | None = end_task
    while cur is not None:
        path.append(cur)
        cur = predecessor.get(cur)
    path.reverse()

    return path, earliest_finish


def build_weekly_schedule(
    order: list[str],
    effort_by_task: dict[str, float],
    duration_weeks: int,
    hours_per_week: float = 20.0,
) -> list[dict]:
    """Greedy bucketing of the topological order into weeks, respecting
    a per-week hour budget. Tasks are not split across weeks in this
    simple v1 scheduler."""
    weeks: list[dict] = [{"week": i + 1, "task_ids": [], "hours": 0.0} for i in range(max(duration_weeks, 1))]
    week_idx = 0

    for task_id in order:
        effort = effort_by_task.get(task_id, 0) or 0
        # advance to next week if this task would overflow the budget
        # (unless it's the first task in an already-empty week, to avoid
        # an infinite skip for a single very large task)
        while (
            weeks[week_idx]["hours"] + effort > hours_per_week
            and weeks[week_idx]["task_ids"]
            and week_idx < len(weeks) - 1
        ):
            week_idx += 1
        weeks[week_idx]["task_ids"].append(task_id)
        weeks[week_idx]["hours"] += effort

    return weeks


def generate_timeline(
    tasks: list[dict],
    dependencies: list[tuple[str, str]],
    start_date,
    duration_weeks: int,
) -> dict:
    """
    tasks: [{"task_id": ..., "estimated_effort_hours": ..., "title": ...}]
    dependencies: [(task_id, depends_on_task_id), ...]
    """
    task_ids = [t["task_id"] for t in tasks]
    effort_by_task = {t["task_id"]: float(t.get("estimated_effort_hours") or 0) for t in tasks}

    order = topological_order(task_ids, dependencies)
    critical_path, earliest_finish = compute_critical_path(task_ids, dependencies, effort_by_task)
    weekly_schedule = build_weekly_schedule(order, effort_by_task, duration_weeks)

    end_date = start_date + timedelta(weeks=duration_weeks) if start_date else None

    milestones = [
        {"name": f"End of Week {w['week']}", "week": w["week"]}
        for w in weekly_schedule
    ]

    return {
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "milestones": milestones,
        "weekly_schedule": weekly_schedule,
        "critical_path": critical_path,
        "execution_order": order,
    }
