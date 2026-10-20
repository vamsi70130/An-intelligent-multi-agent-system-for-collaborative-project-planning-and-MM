"""
Shared agent contract (spec Section 2.2 / Step 26-27).

Every agent is a plain function: (db, project, **kwargs) -> dict.
run_agent() wraps that call with: timing, error handling, and a
persisted AgentLog row -- so every execution is auditable and no
agent's success/failure is ever assumed silently.
"""
import time
import uuid
from typing import Callable

from sqlalchemy.orm import Session

from app.models.development import AgentLog
from app.agents.llm.client import LLMNotConfiguredError, LLMCallError


def run_agent(
    db: Session,
    project_id: uuid.UUID,
    agent_name: str,
    fn: Callable[[], dict],
    input_snapshot: dict | None = None,
    task_id: uuid.UUID | None = None,
) -> dict:
    run_id = str(uuid.uuid4())
    started = time.time()

    log = AgentLog(
        project_id=project_id,
        task_id=task_id,
        agent_name=agent_name,
        run_id=run_id,
        status="running",
        input_snapshot=input_snapshot,
    )
    db.add(log)
    db.commit()

    try:
        output = fn()
        log.status = "success"
        log.output_snapshot = output
        result = {"status": "success", "output": output, "errors": [], "run_id": run_id}
    except LLMNotConfiguredError as e:
        log.status = "failed"
        log.error_message = str(e)
        result = {"status": "not_configured", "output": None, "errors": [str(e)], "run_id": run_id}
    except LLMCallError as e:
        log.status = "failed"
        log.error_message = str(e)
        result = {"status": "failed", "output": None, "errors": [str(e)], "run_id": run_id}
    except Exception as e:  # noqa: BLE001 - agents must never crash the API
        log.status = "failed"
        log.error_message = f"{type(e).__name__}: {e}"
        result = {"status": "failed", "output": None, "errors": [str(e)], "run_id": run_id}
    finally:
        log.duration_ms = int((time.time() - started) * 1000)
        db.add(log)
        db.commit()

    result["agent_name"] = agent_name
    return result
