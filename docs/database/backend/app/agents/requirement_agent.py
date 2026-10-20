"""
Requirement Analysis Agent (spec Step 5 / Section 2.3).

Takes the project's raw idea/description/problem statement/constraints
and asks the configured LLM to produce a structured requirements
analysis. This never returns fabricated content: if no LLM is
configured, app.agents.llm.client raises LLMNotConfiguredError, which
propagates up through run_agent() as status="not_configured".
"""
from app.agents.llm.client import call_llm_json

SYSTEM_PROMPT = """You are a senior software requirements analyst. \
Given a project idea, produce a rigorous requirements analysis. \
Respond with ONLY a JSON object (no markdown fences, no commentary) \
matching exactly this schema:

{
  "project_summary": "string",
  "functional_requirements": [{"ref_code": "FR-1", "text": "string", "priority": "must|should|could"}],
  "non_functional_requirements": [{"ref_code": "NFR-1", "text": "string", "category": "performance|security|usability|reliability|scalability|maintainability"}],
  "user_roles": [{"role": "string", "description": "string"}],
  "constraints": ["string"],
  "assumptions": [{"text": "string", "risk": "low|medium|high"}],
  "acceptance_criteria": ["string"],
  "clarification_questions": ["string"]
}

Rules:
- Do not invent requirements that materially change scope without \
  labeling them under "assumptions" with an appropriate risk level.
- If the idea is ambiguous in a way that matters, add a question to \
  "clarification_questions" instead of guessing silently.
- functional_requirements must be concrete and testable.
"""


def build_user_prompt(project) -> str:
    return f"""Project name: {project.name}
Description: {project.description or "(none provided)"}
Problem statement: {project.problem_statement or "(none provided)"}
Goals: {project.goals or "(none provided)"}
Constraints: {project.constraints_text or "(none provided)"}
Duration (weeks): {project.duration_weeks}
"""


def analyze_requirements(project) -> dict:
    """Pure function: project -> requirements analysis dict.
    Raises LLMNotConfiguredError / LLMCallError on failure (no fallback
    fake output)."""
    user_prompt = build_user_prompt(project)
    result = call_llm_json(SYSTEM_PROMPT, user_prompt)

    # Minimal schema sanity-check so a malformed LLM response fails loudly
    # rather than silently corrupting the DB.
    required_keys = {
        "project_summary", "functional_requirements", "non_functional_requirements",
        "user_roles", "constraints", "assumptions", "acceptance_criteria",
    }
    missing = required_keys - set(result.keys())
    if missing:
        from app.agents.llm.client import LLMCallError
        raise LLMCallError(f"LLM response missing required keys: {missing}")

    return result
