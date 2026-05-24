import pytest

from app.observability.callback import ToolLoggingCallbackHandler


@pytest.mark.asyncio
async def test_callback_logs_tool_call():
    captured = []

    async def fake_record(**kwargs):
        captured.append(kwargs)

    cb = ToolLoggingCallbackHandler(agent_name="qa", record_fn=fake_record)
    run_id = "r1"
    await cb.on_tool_start({"name": "run_tests"}, '{"repo": "x"}', run_id=run_id)
    await cb.on_tool_end('{"passed": true}', run_id=run_id)
    assert captured[0]["agent_name"] == "qa"
    assert captured[0]["skill_requested"] == "run_tests"
    assert captured[0]["status"] == "success"
