import time
from collections.abc import Callable
from typing import Any
from uuid import UUID

from langchain_core.callbacks import AsyncCallbackHandler


class ToolLoggingCallbackHandler(AsyncCallbackHandler):
    """Logs every LangGraph tool call to agent_execution_logs via record_fn."""

    def __init__(self, agent_name: str, record_fn: Callable, **ids: Any):
        self.agent_name = agent_name
        self._record_fn = record_fn
        self._ids = ids  # ticket_execution_id / project_id
        self._inflight: dict[str, dict] = {}

    async def on_tool_start(
        self, serialized: dict, input_str: str, *, run_id: UUID | str, **kwargs
    ):
        self._inflight[str(run_id)] = {
            "name": serialized.get("name", "unknown"),
            "input": input_str,
            "t0": time.monotonic(),
        }

    async def on_tool_end(self, output: str, *, run_id: UUID | str, **kwargs):
        meta = self._inflight.pop(str(run_id), None)
        if not meta:
            return
        await self._record_fn(
            agent_name=self.agent_name,
            skill_requested=meta["name"],
            input_payload={"raw": meta["input"]},
            output_payload={"raw": str(output)},
            status="success",
            duration_ms=int((time.monotonic() - meta["t0"]) * 1000),
            **self._ids,
        )

    async def on_tool_error(self, error: BaseException, *, run_id: UUID | str, **kwargs):
        meta = self._inflight.pop(str(run_id), None)
        if not meta:
            return
        await self._record_fn(
            agent_name=self.agent_name,
            skill_requested=meta["name"],
            input_payload={"raw": meta["input"]},
            output_payload={"error": str(error)},
            status="failed",
            duration_ms=int((time.monotonic() - meta["t0"]) * 1000),
            **self._ids,
        )
