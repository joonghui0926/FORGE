from __future__ import annotations

import os
from typing import Any

import httpx

from forge.integrations.config import required_env


class WorkflowDispatchError(RuntimeError):
    pass


class RenderWorkflowClient:
    """Start durable Render tasks; business decisions remain outside this adapter."""

    def __init__(
        self,
        *,
        api_key: str,
        workflow_slug: str,
        timeout_seconds: float = 30,
        api_base_url: str = "https://api.render.com/v1",
        http_client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.workflow_slug = workflow_slug
        self.timeout_seconds = timeout_seconds
        self.api_base_url = api_base_url.rstrip("/")
        self.http_client = http_client

    @classmethod
    def from_env(cls) -> RenderWorkflowClient:
        return cls(
            api_key=required_env("RENDER_API_KEY"),
            workflow_slug=os.getenv("RENDER_WORKFLOW_SLUG", "forge-control-plane").strip(),
            timeout_seconds=float(os.getenv("RENDER_HTTP_TIMEOUT_SECONDS", "30")),
            api_base_url=os.getenv("RENDER_API_BASE_URL", "https://api.render.com/v1"),
        )

    def start_task(self, task_name: str, input_data: list[Any] | dict[str, Any]) -> str:
        post = self.http_client.post if self.http_client else httpx.post
        response = post(
            f"{self.api_base_url}/task-runs",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"task": f"{self.workflow_slug}/{task_name}", "input": input_data},
            timeout=self.timeout_seconds,
        )
        if response.status_code >= 400:
            raise WorkflowDispatchError(
                f"RENDER_TASK_DISPATCH_FAILED:{response.status_code}:{response.text[:500]}"
            )
        payload = response.json()
        run_id = str(payload.get("id", "")).strip()
        if not run_id:
            raise WorkflowDispatchError("RENDER_TASK_RUN_ID_MISSING")
        return run_id


def start_workflow_task(task_name: str, input_data: list[Any] | dict[str, Any]) -> str:
    """Small compatibility entry point for API routers."""

    return RenderWorkflowClient.from_env().start_task(task_name, input_data)
