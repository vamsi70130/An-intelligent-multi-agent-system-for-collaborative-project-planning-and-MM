"""Technology / Architecture Agent (spec Step 8)."""
from app.agents.llm.client import call_llm_json

SYSTEM_PROMPT = """You are a pragmatic software architect. Given a \
project's requirements and constraints, recommend technologies. \
Respond with ONLY a JSON object matching exactly this schema:

{
  "recommendations": [{
    "category": "frontend|backend|database|ai|auth|deployment|testing",
    "technology": "string",
    "reason": "string",
    "advantages": ["string"],
    "disadvantages": ["string"],
    "compatibility_notes": "string",
    "confidence": 0.0
  }]
}

Rules:
- Base every recommendation on the stated requirements and \
  constraints -- do not recommend technology the constraints rule out.
- Include at least one recommendation per category listed above that \
  is actually relevant to this project (skip a category only if it \
  genuinely does not apply, e.g. no "ai" category for a project with \
  no AI/ML component).
- confidence is a number between 0 and 1.
"""


def build_user_prompt(project, functional_requirements: list[str]) -> str:
    reqs_text = "\n".join(f"- {r}" for r in functional_requirements) or "(none)"
    return f"""Project name: {project.name}
Constraints: {project.constraints_text or "(none)"}
Available technologies the team already knows: {project.available_technologies or "(none specified)"}

Functional requirements:
{reqs_text}
"""


def recommend_technologies(project, functional_requirements: list[str]) -> dict:
    user_prompt = build_user_prompt(project, functional_requirements)
    result = call_llm_json(SYSTEM_PROMPT, user_prompt)
    if "recommendations" not in result:
        from app.agents.llm.client import LLMCallError
        raise LLMCallError("LLM response missing 'recommendations' key")
    return result
