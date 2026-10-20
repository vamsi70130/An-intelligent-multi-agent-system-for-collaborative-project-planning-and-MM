"""
Project Decomposition Agent (spec Step 7 / Section 2.3 C).

Converts requirements + research into modules and tasks with explicit
dependencies (referenced by temporary in-response codes, resolved to
real DB IDs by the caller).
"""
from app.agents.llm.client import call_llm_json

SYSTEM_PROMPT = """You are a project planning agent. Given a project's \
requirements and research notes, decompose the project into modules \
and concrete tasks. Respond with ONLY a JSON object (no markdown \
fences, no commentary) matching exactly this schema:

{
  "modules": [{"module_ref": "MOD-1", "name": "string", "description": "string"}],
  "tasks": [{
    "task_ref": "TASK-1",
    "title": "string",
    "description": "string",
    "module_ref": "MOD-1",
    "priority": "high|medium|low",
    "estimated_effort_hours": 8,
    "depends_on_refs": ["TASK-0"],
    "acceptance_criteria": ["string"],
    "required_skills": ["string"],
    "expected_artifact": "string",
    "verification_method": "automated_tests|manual_review|evidence_review"
  }]
}

Rules:
- Use "task_ref" and "module_ref" as temporary identifiers local to \
  this response (e.g. "TASK-1", "MOD-1") -- the caller will map these \
  to real IDs.
- depends_on_refs must only reference task_refs defined earlier or \
  elsewhere in this same response. Do not create circular dependencies.
- Every task must have at least one concrete, testable acceptance \
  criterion.
- Keep tasks reasonably sized (a few hours to a few days of effort \
  each) -- do not produce one giant task per module.
"""


def build_user_prompt(project, functional_requirements: list[str], research_summary: str) -> str:
    reqs_text = "\n".join(f"- {r}" for r in functional_requirements) or "(none)"
    return f"""Project name: {project.name}
Duration (weeks): {project.duration_weeks}

Functional requirements:
{reqs_text}

Research notes:
{research_summary or "(none)"}
"""


def decompose_project(project, functional_requirements: list[str], research_summary: str = "") -> dict:
    user_prompt = build_user_prompt(project, functional_requirements, research_summary)
    result = call_llm_json(SYSTEM_PROMPT, user_prompt)

    required_keys = {"modules", "tasks"}
    missing = required_keys - set(result.keys())
    if missing:
        from app.agents.llm.client import LLMCallError
        raise LLMCallError(f"LLM response missing required keys: {missing}")

    return result
