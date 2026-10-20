"""
Task Allocation Agent (spec Step 10).

Deliberately deterministic/rule-based rather than LLM-based: task
assignment needs to be reproducible and auditable, and a simple
skill/workload matching algorithm is more reliable here than an LLM
guess. This mirrors the architecture doc's principle of using the
right tool for each job rather than routing everything through an LLM.
"""


def allocate_tasks(tasks: list[dict], team_members: list[str]) -> list[dict]:
    """
    tasks: [{"task_id": ..., "required_skills": [...], "priority": ...}]
    team_members: ["Alex (backend)", "Priya (frontend)", ...]

    Returns: [{"task_id": ..., "assignee_type": "human|ai", "assignee_label": ..., "rationale": ...}]
    """
    assignments = []
    workload: dict[str, int] = {m: 0 for m in team_members}

    for task in tasks:
        required_skills = [s.lower() for s in (task.get("required_skills") or [])]
        candidates = [
            m for m in team_members
            if any(skill in m.lower() for skill in required_skills)
        ]

        if candidates:
            # pick the least-loaded matching human
            chosen = min(candidates, key=lambda m: workload.get(m, 0))
            workload[chosen] = workload.get(chosen, 0) + 1
            assignments.append({
                "task_id": task["task_id"],
                "assignee_type": "human",
                "assignee_label": chosen,
                "rationale": f"Matched required skills {required_skills} to team member profile.",
            })
        elif any(s in ("coding", "development", "implementation", "testing", "debugging") for s in required_skills):
            assignments.append({
                "task_id": task["task_id"],
                "assignee_type": "ai",
                "assignee_label": "Coding Agent",
                "rationale": "No human team member's listed skills matched; routed to the AI Coding Agent.",
            })
        elif team_members:
            chosen = min(team_members, key=lambda m: workload.get(m, 0))
            workload[chosen] = workload.get(chosen, 0) + 1
            assignments.append({
                "task_id": task["task_id"],
                "assignee_type": "human",
                "assignee_label": chosen,
                "rationale": "No specific skill match found; assigned to least-loaded team member.",
            })
        else:
            assignments.append({
                "task_id": task["task_id"],
                "assignee_type": "ai",
                "assignee_label": "Coding Agent",
                "rationale": "No team members configured for this project; defaulted to AI Coding Agent.",
            })

    return assignments
