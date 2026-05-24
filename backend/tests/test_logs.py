import pytest
from sqlalchemy import select

from app.db.base import SessionLocal
from app.db.logs import record_agent_log
from app.db.models import AgentExecutionLog


@pytest.mark.asyncio
async def test_record_agent_log_inserts_row():
    async with SessionLocal() as s:
        await record_agent_log(
            s,
            agent_name="pm",
            skill_requested="confluence_create_page",
            input_payload={"title": "x"},
            output_payload={"id": "1"},
            status="success",
            token_usage=42,
            duration_ms=10,
        )
        await s.commit()
        rows = (
            await s.execute(
                select(AgentExecutionLog).where(AgentExecutionLog.agent_name == "pm")
            )
        ).scalars().all()
    assert rows and rows[0].token_usage == 42
