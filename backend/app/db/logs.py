import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentExecutionLog


async def record_agent_log(
    session: AsyncSession,
    *,
    agent_name: str,
    skill_requested: str | None = None,
    input_payload: dict | None = None,
    output_payload: dict | None = None,
    status: str | None = None,
    token_usage: int | None = None,
    duration_ms: int | None = None,
    ticket_execution_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
) -> AgentExecutionLog:
    row = AgentExecutionLog(
        agent_name=agent_name,
        skill_requested=skill_requested,
        input_payload=input_payload,
        output_payload=output_payload,
        status=status,
        token_usage=token_usage,
        duration_ms=duration_ms,
        ticket_execution_id=ticket_execution_id,
        project_id=project_id,
    )
    session.add(row)
    await session.flush()
    return row
