import pytest

from app.mcp.client import MCPClientManager
from app.mcp.tool_scopes import AGENT_TOOL_SCOPES


class _Tool:
    def __init__(self, name):
        self.name = name


@pytest.mark.asyncio
async def test_tools_for_filters_by_scope(monkeypatch):
    # Provide all architecture-scoped tools plus an extra one not in scope
    arch_tools = [_Tool(n) for n in AGENT_TOOL_SCOPES["architecture"]]
    extra = _Tool("merge_pull_request")  # only in review scope, not architecture
    fake_tools = arch_tools + [extra]

    mgr = MCPClientManager(servers={})
    monkeypatch.setattr(mgr, "_load_all_tools", lambda: _coro(fake_tools))
    await mgr.startup()

    arch = [t.name for t in mgr.tools_for("architecture")]
    assert "create_repository" in arch
    assert "merge_pull_request" not in arch


async def _coro(v):
    return v
