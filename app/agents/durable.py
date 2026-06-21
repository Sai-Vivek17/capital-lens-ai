"""Durable agent execution utilities for Phase 2 orchestration."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Generic, TypeVar

from app.schemas.models import AgentStep, ResearchRequest
from app.storage.database import complete_agent_run, create_agent_run, record_agent_event

T = TypeVar("T")
ProgressCallback = Callable[[AgentStep], None]


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    backoff_seconds: float = 0.15


class DurableAgentExecutor:
    """Runs agent steps with retries, event persistence, and progress callbacks."""

    def __init__(
        self,
        request: ResearchRequest,
        db_path: Path,
        steps: list[AgentStep],
        progress_callback: ProgressCallback | None = None,
        retry_policy: RetryPolicy | None = None,
        run_id: str | None = None,
    ) -> None:
        self.run_id = run_id or str(uuid.uuid4())
        self.request = request
        self.db_path = db_path
        self.steps = steps
        self.progress_callback = progress_callback
        self.retry_policy = retry_policy or RetryPolicy()
        create_agent_run(self.run_id, request.query, request.mode, db_path=self.db_path)

    def emit(self, name: str, status: str, detail: str, attempt: int = 1, error: str | None = None) -> None:
        step = AgentStep(name=name, status=status, detail=detail)  # type: ignore[arg-type]
        self.steps.append(step)
        record_agent_event(
            run_id=self.run_id,
            agent_name=name,
            attempt=attempt,
            status=status,
            detail=detail,
            error=error,
            db_path=self.db_path,
        )
        if self.progress_callback:
            self.progress_callback(step)

    def execute(
        self,
        name: str,
        running_detail: str,
        operation: Callable[[], T],
        success_detail: Callable[[T], str],
    ) -> T:
        last_error: Exception | None = None
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            self.emit(name, "running", running_detail if attempt == 1 else f"{running_detail} Retry {attempt}.", attempt=attempt)
            try:
                result = operation()
                self.emit(name, "complete", success_detail(result), attempt=attempt)
                return result
            except Exception as exc:
                last_error = exc
                if attempt >= self.retry_policy.max_attempts:
                    detail = f"{name} failed after {attempt} attempt(s): {exc}"
                    self.emit(name, "error", detail, attempt=attempt, error=str(exc))
                    complete_agent_run(self.run_id, "failed", error=str(exc), db_path=self.db_path)
                    raise
                detail = f"{name} attempt {attempt} failed: {exc}. Retrying with fallback-safe execution."
                self.emit(name, "warning", detail, attempt=attempt, error=str(exc))
                time.sleep(self.retry_policy.backoff_seconds * attempt)
        raise RuntimeError(f"{name} failed unexpectedly: {last_error}")

    def complete(self) -> None:
        complete_agent_run(self.run_id, "complete", db_path=self.db_path)

