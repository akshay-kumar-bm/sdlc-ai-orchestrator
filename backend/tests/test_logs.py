from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.logs import record_agent_log


@pytest.mark.asyncio
async def test_record_agent_log_inserts_row():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    row = await record_agent_log(
        session,
        agent_name="pm",
        skill_requested="confluence_create_page",
        input_payload={"title": "x"},
        output_payload={"id": "1"},
        status="success",
        token_usage=42,
        duration_ms=10,
    )

    session.add.assert_called_once_with(row)
    session.flush.assert_awaited_once()
    assert row.agent_name == "pm"
    assert row.token_usage == 42
