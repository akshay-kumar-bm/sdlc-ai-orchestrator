from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

from app.mcp.tool_scopes import AGENT_TOOL_SCOPES


class MCPClientManager:
    """Connects to configured MCP servers and hands each agent its scoped toolset."""

    def __init__(self, servers: dict[str, dict[str, Any]]):
        self._servers = servers
        self._client: MultiServerMCPClient | None = None
        self._tools_by_name: dict[str, Any] = {}

    async def _load_all_tools(self):
        self._client = MultiServerMCPClient(self._servers)
        return await self._client.get_tools()

    async def startup(self) -> None:
        tools = await self._load_all_tools()
        self._tools_by_name = {t.name: t for t in tools}

    def tools_for(self, agent: str) -> list[Any]:
        scope = AGENT_TOOL_SCOPES.get(agent, [])
        missing = [n for n in scope if n not in self._tools_by_name]
        if missing:
            raise KeyError(f"Agent '{agent}' requested unavailable MCP tools: {missing}")
        return [self._tools_by_name[n] for n in scope]

    def available_tool_names(self) -> list[str]:
        return sorted(self._tools_by_name)
