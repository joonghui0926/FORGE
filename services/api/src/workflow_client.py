from __future__ import annotations

import os
from typing import Any

import httpx


class WorkflowDispatchError(RuntimeError):
    pass


def start_workflow_task(task_name: str, input_data: list[Any] | dict[str, Any]) -> str:
    api_key = os.getenv("RENDER_API_KEY", "").strip()
    workflow_slug = os.getenv("RENDER_WORKFLOW_SLUG", "forge-control-plane").strip()
    if not api_key:
        raise WorkflowDispatchError("RENDER_API_KEY_NOT_CONFIGURED")
    response = httpx.post(
        "https://api.render.com/v1/task-runs",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"task": f"{workflow_slug}/{task_name}", "input": input_data},
        timeout=30,
    )
    if response.status_code >= 400:
        raise WorkflowDispatchError(
            f"RENDER_TASK_DISPATCH_FAILED:{response.status_code}:{response.text[:500]}"
        )
    payload = response.json()
    run_id = str(payload.get("id", ""))
    if not run_id:
        raise WorkflowDispatchError("RENDER_TASK_RUN_ID_MISSING")
    return run_id
