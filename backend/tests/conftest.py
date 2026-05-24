import os

# Set required env vars before any app module is imported.
# These override .env file values (env vars take priority in pydantic-settings).
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/aeo_test")

# Prevent real mcp_servers.json from loading during unit tests.
# Empty string overrides the MCP_SERVERS_FILE=... line in .env.
os.environ["MCP_SERVERS_FILE"] = ""
os.environ.setdefault("MCP_SERVERS", "{}")
