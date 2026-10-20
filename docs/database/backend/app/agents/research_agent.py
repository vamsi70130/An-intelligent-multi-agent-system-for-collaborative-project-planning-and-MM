"""
Research Agent (spec Step 6 / Section 2.3).

Produces domain research suggestions from the project's requirements.
Explicitly distinguishes AI-generated suggestions from verified
external references, per Step 6's instruction not to invent citations:
the agent is told to leave source_url null/omit it unless it is
confident of a real, well-known reference, and every item is tagged
is_ai_generated=True by default -- nothing here is presented as a
"verified" citation.
"""
from app.agents.llm.client import call_llm_json

SYSTEM_PROMPT = """You are a research assistant supporting a software \
engineering project. Given a project summary and its functional \
requirements, propose relevant technologies, algorithms/methodologies, \
existing approaches, and research gaps. Respond with ONLY a JSON \
object (no markdown fences, no commentary) matching exactly this \
schema:

{
  "relevant_technologies": ["string"],
  "algorithms_or_methods": [{"name": "string", "use_case": "string"}],
  "existing_approaches": [{"name": "string", "summary": "string"}],
  "research_gaps": ["string"],
  "references": [{"title": "string", "note": "string"}]
}

Rules:
- Do NOT invent citations, URLs, DOIs, or author names. Only include \
  an item under "references" if it is a well-known, real work you are \
  confident exists (e.g. a well-known textbook, a widely cited paper \
  by name, an official technology's own documentation). Otherwise \
  omit it entirely rather than guessing.
- Never fabricate a URL. If you don't have one you're confident is \
  real, leave it out of the note field -- do not invent one.
- Keep "existing_approaches" about real, general classes of solution \
  (e.g. "rule-based scheduling engines"), not specific fabricated \
  product names you're unsure about.
"""


def build_user_prompt(project, functional_requirements: list[str]) -> str:
    reqs_text = "\n".join(f"- {r}" for r in functional_requirements) or "(none yet)"
    return f"""Project name: {project.name}
Description: {project.description or "(none provided)"}
Problem statement: {project.problem_statement or "(none provided)"}

Functional requirements so far:
{reqs_text}
"""


def research_project(project, functional_requirements: list[str]) -> dict:
    user_prompt = build_user_prompt(project, functional_requirements)
    result = call_llm_json(SYSTEM_PROMPT, user_prompt)

    required_keys = {"relevant_technologies", "algorithms_or_methods", "existing_approaches", "research_gaps"}
    missing = required_keys - set(result.keys())
    if missing:
        from app.agents.llm.client import LLMCallError
        raise LLMCallError(f"LLM response missing required keys: {missing}")

    return result
