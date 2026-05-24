from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.mcp.client import MCPClientManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    mgr = MCPClientManager(servers=get_settings().MCP_SERVERS)
    await mgr.startup()
    app.state.mcp = mgr
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="AEO Orchestrator", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/mcp")
    def health_mcp() -> dict[str, list[str]]:
        mgr: MCPClientManager = app.state.mcp
        return {"tools": mgr.available_tool_names()}

    return app


app = create_app()
