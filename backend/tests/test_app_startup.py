from fastapi.testclient import TestClient

from app.main import create_app


def test_mcp_debug_endpoint(monkeypatch):
    async def fake_startup(self):
        self._tools_by_name = {"confluence_get_page": object()}

    monkeypatch.setattr("app.mcp.client.MCPClientManager.startup", fake_startup)
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/health/mcp")
        assert resp.status_code == 200
        assert "confluence_get_page" in resp.json()["tools"]
