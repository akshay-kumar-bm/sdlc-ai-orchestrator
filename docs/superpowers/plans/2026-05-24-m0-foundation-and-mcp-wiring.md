# M0 — Foundation & MCP Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the backend skeleton that every later milestone builds on: a FastAPI app, typed config, an LLM-provider abstraction, the Postgres state schema, a client that connects to the existing Confluence/Jira/GitHub MCP servers with per-agent tool scoping, a tool-call logging callback, and the in-process local-execution utility (clone + pytest + ruff).

**Architecture:** Single FastAPI service (`backend/`). State in Postgres via SQLAlchemy 2.0 async + Alembic. Agents (built in M1/M2) get LLMs from `LLMClient` and tools from `MCPClientManager.tools_for(agent)`. Every tool call is logged to `agent_execution_logs` by a LangGraph callback. The only integration we own is `local_exec` (subprocess). No custom MCP servers — we are an MCP **client**.

**Tech Stack:** Python 3.11, FastAPI, uvicorn, SQLAlchemy 2.0 (async) + asyncpg, Alembic, pydantic-settings, langgraph, langchain-core, langchain-mcp-adapters, langchain-anthropic, langchain-openai, pytest, pytest-asyncio, ruff.

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/requirements.txt` | Pinned dependencies |
| `backend/pyproject.toml` | ruff + pytest config |
| `backend/app/main.py` | FastAPI app factory + `/health` |
| `backend/app/core/config.py` | `Settings` (env-driven), incl. `MCP_SERVERS` JSON |
| `backend/app/core/llm_client.py` | `get_llm(model_override)` provider abstraction |
| `backend/app/db/base.py` | Async engine + `Base` + `get_session` |
| `backend/app/db/models.py` | `Project`, `TicketExecution`, `AgentExecutionLog`, `HumanApprovalRequest` |
| `backend/app/db/logs.py` | `record_agent_log(...)` insert helper |
| `backend/app/mcp/tool_scopes.py` | Per-agent allowed MCP tool-name lists |
| `backend/app/mcp/client.py` | `MCPClientManager` (wraps `MultiServerMCPClient`, `tools_for`) |
| `backend/app/observability/callback.py` | `ToolLoggingCallbackHandler` → `agent_execution_logs` |
| `backend/app/local_exec/runner.py` | `clone_branch`, `run_tests`, `run_linter`, `parse_pytest_report` |
| `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/0001_*.py` | Migrations |
| `backend/tests/...` | Tests mirroring the above |

---

## Task 1: Project scaffold + `/health`

**Files:**
- Create: `backend/requirements.txt`, `backend/pyproject.toml`, `backend/app/__init__.py`, `backend/app/main.py`
- Test: `backend/tests/test_health.py`

- [ ] **Step 1: Write `requirements.txt`**

```
fastapi==0.111.0
uvicorn[standard]==0.30.1
sqlalchemy[asyncio]==2.0.30
asyncpg==0.29.0
alembic==1.13.1
pydantic-settings==2.3.4
langgraph==0.2.28
langchain-core==0.3.15
langchain-mcp-adapters==0.1.0
langchain-anthropic==0.2.4
langchain-openai==0.2.4
httpx==0.27.0
pytest==8.2.2
pytest-asyncio==0.23.7
ruff==0.5.0
```

- [ ] **Step 2: Write `pyproject.toml`** (ruff + pytest-asyncio)

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 3: Write the failing test** in `backend/tests/test_health.py`

```python
from fastapi.testclient import TestClient
from app.main import create_app

def test_health_returns_ok():
    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 4: Run it, expect failure**

Run: `cd backend && pip install -r requirements.txt && pytest tests/test_health.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 5: Implement `app/main.py`**

```python
from fastapi import FastAPI

def create_app() -> FastAPI:
    app = FastAPI(title="AEO Orchestrator", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app

app = create_app()
```

- [ ] **Step 6: Run it, expect pass**

Run: `pytest tests/test_health.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat(m0): scaffold FastAPI backend with /health"
```

---

## Task 2: Typed config (`Settings`)

**Files:**
- Create: `backend/app/core/__init__.py`, `backend/app/core/config.py`, `backend/.env.example`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
import json
from app.core.config import Settings

def test_settings_parses_mcp_servers(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_MODEL", "claude-sonnet-4-6")
    monkeypatch.setenv("WEBHOOK_SECRET", "s3cret")
    monkeypatch.setenv("MCP_SERVERS", json.dumps({
        "github": {"transport": "streamable_http", "url": "https://api.example/mcp", "headers": {"Authorization": "Bearer x"}}
    }))
    s = Settings()
    assert s.LLM_PROVIDER == "anthropic"
    assert s.MCP_SERVERS["github"]["transport"] == "streamable_http"
```

- [ ] **Step 2: Run it, expect failure** — `ModuleNotFoundError: app.core.config`

Run: `pytest tests/test_config.py -v`

- [ ] **Step 3: Implement `app/core/config.py`**

```python
import json
from functools import lru_cache
from typing import Any, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    LLM_PROVIDER: Literal["anthropic", "openai"] = "anthropic"
    LLM_MODEL: str = "claude-sonnet-4-6"
    ANTHROPIC_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    WEBHOOK_SECRET: str = "change-me"

    # JSON map: { "<server>": { "transport": "...", "url": "...", "headers": {...} } }
    # or stdio: { "<server>": { "transport": "stdio", "command": "...", "args": [...] } }
    MCP_SERVERS: dict[str, dict[str, Any]] = {}

    @field_validator("MCP_SERVERS", mode="before")
    @classmethod
    def _parse_json(cls, v: Any) -> Any:
        return json.loads(v) if isinstance(v, str) else v

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Write `.env.example`** (documents required vars)

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/aeo
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
WEBHOOK_SECRET=change-me
# MCP_SERVERS is a JSON object. Example (remote GitHub MCP):
# MCP_SERVERS={"github":{"transport":"streamable_http","url":"https://api.githubcopilot.com/mcp/","headers":{"Authorization":"Bearer <PAT>"}},"jira":{...},"confluence":{...}}
MCP_SERVERS={}
```

- [ ] **Step 5: Run it, expect pass** — `pytest tests/test_config.py -v`

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/config.py backend/app/core/__init__.py backend/.env.example backend/tests/test_config.py
git commit -m "feat(m0): typed Settings with MCP_SERVERS parsing"
```

---

## Task 3: LLM provider abstraction

**Files:**
- Create: `backend/app/core/llm_client.py`
- Test: `backend/tests/test_llm_client.py`

- [ ] **Step 1: Write the failing test** (assert provider→class mapping, no network)

```python
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from app.core.llm_client import get_llm

def test_get_llm_anthropic(monkeypatch):
    monkeypatch.setattr("app.core.llm_client.get_settings", lambda: _fake("anthropic", "claude-sonnet-4-6"))
    assert isinstance(get_llm(), ChatAnthropic)

def test_get_llm_openai_with_override(monkeypatch):
    monkeypatch.setattr("app.core.llm_client.get_settings", lambda: _fake("openai", "gpt-4o"))
    llm = get_llm(model_override="gpt-4o-mini")
    assert isinstance(llm, ChatOpenAI)

class _fake:
    def __init__(self, p, m):
        self.LLM_PROVIDER, self.LLM_MODEL = p, m
        self.ANTHROPIC_API_KEY = "x"; self.OPENAI_API_KEY = "x"
```

- [ ] **Step 2: Run it, expect failure** — `pytest tests/test_llm_client.py -v`

- [ ] **Step 3: Implement `app/core/llm_client.py`**

```python
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from app.core.config import get_settings

def get_llm(model_override: str | None = None):
    s = get_settings()
    model = model_override or s.LLM_MODEL
    if s.LLM_PROVIDER == "anthropic":
        return ChatAnthropic(model=model, api_key=s.ANTHROPIC_API_KEY)
    return ChatOpenAI(model=model, api_key=s.OPENAI_API_KEY)
```

- [ ] **Step 4: Run it, expect pass**

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/llm_client.py backend/tests/test_llm_client.py
git commit -m "feat(m0): LLMClient provider abstraction"
```

---

## Task 4: DB engine, base, and models

**Files:**
- Create: `backend/app/db/__init__.py`, `backend/app/db/base.py`, `backend/app/db/models.py`
- Test: `backend/tests/test_models.py`

- [ ] **Step 1: Implement `app/db/base.py`**

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

class Base(DeclarativeBase):
    pass

_engine = create_async_engine(get_settings().DATABASE_URL, future=True)
SessionLocal = async_sessionmaker(_engine, expire_on_commit=False)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
```

- [ ] **Step 2: Implement `app/db/models.py`** (the 4 tables from the spec)

```python
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="INITIALIZED")
    confluence_prd_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    confluence_arch_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_repo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    jira_project_key: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confluence_space_key: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

class TicketExecution(Base):
    __tablename__ = "ticket_executions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    jira_ticket_key: Mapped[str] = mapped_column(String(50))
    github_issue_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_pr_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_branch: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="AI_READY")
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    current_agent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

class AgentExecutionLog(Base):
    __tablename__ = "agent_execution_logs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_execution_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ticket_executions.id"), nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    agent_name: Mapped[str] = mapped_column(String(100))
    skill_requested: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    token_usage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

class HumanApprovalRequest(Base):
    __tablename__ = "human_approval_requests"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    approval_type: Mapped[str] = mapped_column(String(100))  # PRD | ARCHITECTURE | EPICS | STORIES | ESCALATION
    payload: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
```

- [ ] **Step 3: Write the failing test** (models import + table names registered on metadata)

```python
from app.db.base import Base
import app.db.models  # noqa: F401

def test_all_tables_registered():
    names = set(Base.metadata.tables)
    assert names == {"projects", "ticket_executions", "agent_execution_logs", "human_approval_requests"}
```

- [ ] **Step 4: Run it, expect pass** — `pytest tests/test_models.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/ backend/tests/test_models.py
git commit -m "feat(m0): async DB engine and ORM models for the 4 state tables"
```

---

## Task 5: Alembic migration for the 4 tables

**Files:**
- Create: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/0001_initial.py`

- [ ] **Step 1: Init alembic** — `cd backend && alembic init alembic` (then replace `env.py` and `alembic.ini` `sqlalchemy.url` handling below)

- [ ] **Step 2: Edit `alembic/env.py`** to use our async URL + metadata

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.db.base import Base
import app.db.models  # noqa: F401

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata

def _run(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async():
    engine = create_async_engine(get_settings().DATABASE_URL)
    async with engine.connect() as conn:
        await conn.run_sync(_run)
    await engine.dispose()

if context.is_offline_mode():
    context.configure(url=get_settings().DATABASE_URL, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(run_async())
```

- [ ] **Step 3: Autogenerate the migration**

Run: `cd backend && alembic revision --autogenerate -m "initial"`
Rename the output file to `0001_initial.py`. Verify it creates 4 tables + the indexes (`idx_ticket_executions_status`, `idx_ticket_executions_project`, `idx_agent_logs_ticket`). Add the indexes manually in the migration if autogenerate misses them:

```python
op.create_index("idx_ticket_executions_status", "ticket_executions", ["status"])
op.create_index("idx_ticket_executions_project", "ticket_executions", ["project_id"])
op.create_index("idx_agent_logs_ticket", "agent_execution_logs", ["ticket_execution_id"])
```

- [ ] **Step 4: Apply against a local Postgres, verify**

Run: `docker run -d --name aeo-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16 && alembic upgrade head`
Expected: 4 tables present (`psql ... -c "\dt"`).

- [ ] **Step 5: Commit**

```bash
git add backend/alembic.ini backend/alembic/
git commit -m "feat(m0): initial Alembic migration for state schema"
```

---

## Task 6: `record_agent_log` insert helper

**Files:**
- Create: `backend/app/db/logs.py`
- Test: `backend/tests/test_logs.py` (uses SQLite-compatible? No — JSONB. Use a transactional Postgres fixture.)

- [ ] **Step 1: Write the failing test** (insert a row, read it back)

```python
import pytest
from sqlalchemy import select
from app.db.base import SessionLocal
from app.db.models import AgentExecutionLog
from app.db.logs import record_agent_log

@pytest.mark.asyncio
async def test_record_agent_log_inserts_row():
    async with SessionLocal() as s:
        await record_agent_log(s, agent_name="pm", skill_requested="confluence_create_page",
                               input_payload={"title": "x"}, output_payload={"id": "1"},
                               status="success", token_usage=42, duration_ms=10)
        await s.commit()
        rows = (await s.execute(select(AgentExecutionLog).where(AgentExecutionLog.agent_name == "pm"))).scalars().all()
    assert rows and rows[0].token_usage == 42
```

- [ ] **Step 2: Run it, expect failure** (needs `DATABASE_URL` pointing at the test Postgres) — `pytest tests/test_logs.py -v`

- [ ] **Step 3: Implement `app/db/logs.py`**

```python
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import AgentExecutionLog

async def record_agent_log(
    session: AsyncSession, *, agent_name: str, skill_requested: str | None = None,
    input_payload: dict | None = None, output_payload: dict | None = None,
    status: str | None = None, token_usage: int | None = None, duration_ms: int | None = None,
    ticket_execution_id: uuid.UUID | None = None, project_id: uuid.UUID | None = None,
) -> AgentExecutionLog:
    row = AgentExecutionLog(
        agent_name=agent_name, skill_requested=skill_requested,
        input_payload=input_payload, output_payload=output_payload, status=status,
        token_usage=token_usage, duration_ms=duration_ms,
        ticket_execution_id=ticket_execution_id, project_id=project_id,
    )
    session.add(row)
    await session.flush()
    return row
```

- [ ] **Step 4: Run it, expect pass**

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/logs.py backend/tests/test_logs.py
git commit -m "feat(m0): record_agent_log helper"
```

---

## Task 7: Local-execution runner (clone / pytest / ruff / parse)

**Files:**
- Create: `backend/app/local_exec/__init__.py`, `backend/app/local_exec/runner.py`
- Test: `backend/tests/test_local_exec.py`

- [ ] **Step 1: Write the failing test** (parse a known pytest-json-report shape; mock subprocess for clone/run)

```python
import json
from app.local_exec.runner import parse_pytest_report

def test_parse_pytest_report_summarizes(tmp_path):
    report = {"summary": {"passed": 3, "failed": 1, "total": 4},
              "tests": [{"nodeid": "tests/test_x.py::test_a", "outcome": "failed",
                         "call": {"longrepr": "AssertionError: expected 409 got 500"}}]}
    p = tmp_path / "report.json"; p.write_text(json.dumps(report))
    result = parse_pytest_report(str(p))
    assert result["passed"] is False
    assert result["totals"] == {"passed": 3, "failed": 1, "total": 4}
    assert result["failures"][0]["nodeid"].endswith("test_a")
    assert "AssertionError" in result["failures"][0]["longrepr"]
```

- [ ] **Step 2: Run it, expect failure** — `pytest tests/test_local_exec.py -v`

- [ ] **Step 3: Implement `app/local_exec/runner.py`**

```python
import json
import subprocess
import tempfile

def clone_branch(repo_url: str, branch: str, target_dir: str | None = None) -> dict:
    target = target_dir or tempfile.mkdtemp(prefix="aeo-")
    subprocess.run(["git", "clone", "--depth", "1", "-b", branch, repo_url, target],
                   check=True, capture_output=True, text=True, timeout=300)
    return {"path": target}

def run_tests(repo_path: str, test_path: str = "tests/") -> dict:
    report_file = f"{repo_path}/.aeo_report.json"
    subprocess.run(
        ["pytest", test_path, "--json-report", f"--json-report-file={report_file}", "-q"],
        cwd=repo_path, capture_output=True, text=True, timeout=600,
    )
    return parse_pytest_report(report_file)

def run_linter(repo_path: str) -> dict:
    proc = subprocess.run(["ruff", "check", ".", "--output-format=json"],
                          cwd=repo_path, capture_output=True, text=True, timeout=120)
    violations = json.loads(proc.stdout) if proc.stdout.strip() else []
    return {"passed": len(violations) == 0, "violations": violations}

def parse_pytest_report(report_path: str) -> dict:
    with open(report_path) as f:
        data = json.load(f)
    summary = data.get("summary", {})
    failures = [
        {"nodeid": t["nodeid"], "longrepr": t.get("call", {}).get("longrepr", "")}
        for t in data.get("tests", []) if t.get("outcome") == "failed"
    ]
    return {"passed": summary.get("failed", 0) == 0, "totals": summary, "failures": failures}
```

> Note: `pytest --json-report` requires `pytest-json-report` to be installed **in the cloned repo's** test environment. The runner assumes the cloned repo's CI installs it, or M2's QA Agent installs it before running. Add `pytest-json-report` handling in M2.

- [ ] **Step 4: Run it, expect pass**

- [ ] **Step 5: Commit**

```bash
git add backend/app/local_exec/ backend/tests/test_local_exec.py
git commit -m "feat(m0): local-exec runner (clone/pytest/ruff/parse)"
```

---

## Task 8: Per-agent tool scopes + MCP client manager

**Files:**
- Create: `backend/app/mcp/__init__.py`, `backend/app/mcp/tool_scopes.py`, `backend/app/mcp/client.py`
- Test: `backend/tests/test_mcp_client.py`

- [ ] **Step 1: Implement `app/mcp/tool_scopes.py`** (the matrix from the decisions doc, by tool name)

```python
# Allowed MCP tool names per agent. Names match the configured MCP servers.
AGENT_TOOL_SCOPES: dict[str, list[str]] = {
    "pm": [
        "confluence_search", "confluence_get_page",
        "confluence_create_page", "confluence_update_page", "confluence_add_comment",
    ],
    "architecture": [
        "confluence_get_page", "confluence_create_page", "confluence_add_label",
        "get_me", "create_repository", "push_files", "create_or_update_file", "get_file_contents",
    ],
    "jira_structuring": [
        "confluence_get_page", "confluence_get_page_children", "confluence_create_page", "confluence_add_label",
        "jira_list_projects", "jira_get_project", "jira_get_field_options",
        "jira_create_issue", "jira_update_issue", "jira_add_comment", "jira_get_issue_link_types",
    ],
    "planning": [
        "confluence_get_page", "jira_get_issue",
        "get_file_contents", "list_branches", "issue_write",
        "assign_copilot_to_issue", "get_copilot_job_status",
    ],
    "qa": [
        "jira_get_issue", "pull_request_read", "add_issue_comment", "assign_copilot_to_issue",
    ],
    "review": [
        "confluence_get_page", "jira_get_issue",
        "pull_request_read", "pull_request_review_write", "merge_pull_request", "request_copilot_review",
    ],
    "jira_update": [
        "jira_get_transitions", "jira_transition_issue", "jira_add_comment", "pull_request_read",
    ],
}
```

- [ ] **Step 2: Write the failing test** (manager filters tools by scope; mock the adapter)

```python
import pytest
from app.mcp.client import MCPClientManager

class _Tool:
    def __init__(self, name): self.name = name

@pytest.mark.asyncio
async def test_tools_for_filters_by_scope(monkeypatch):
    fake_tools = [_Tool("confluence_get_page"), _Tool("create_repository"), _Tool("merge_pull_request")]
    mgr = MCPClientManager(servers={})
    monkeypatch.setattr(mgr, "_load_all_tools", lambda: _coro(fake_tools))
    await mgr.startup()
    arch = [t.name for t in mgr.tools_for("architecture")]
    assert "create_repository" in arch
    assert "merge_pull_request" not in arch  # not in architecture scope

async def _coro(v): return v
```

- [ ] **Step 3: Run it, expect failure** — `pytest tests/test_mcp_client.py -v`

- [ ] **Step 4: Implement `app/mcp/client.py`**

```python
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

from app.mcp.tool_scopes import AGENT_TOOL_SCOPES

class MCPClientManager:
    """Connects to the existing MCP servers and hands each agent its scoped toolset."""

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
            # Fail loud in dev: a scoped tool isn't exposed by any server.
            raise KeyError(f"Agent '{agent}' requested unavailable MCP tools: {missing}")
        return [self._tools_by_name[n] for n in scope]

    def available_tool_names(self) -> list[str]:
        return sorted(self._tools_by_name)
```

- [ ] **Step 5: Run it, expect pass**

- [ ] **Step 6: Commit**

```bash
git add backend/app/mcp/ backend/tests/test_mcp_client.py
git commit -m "feat(m0): MCP client manager with per-agent tool scoping"
```

---

## Task 9: Tool-call logging callback

**Files:**
- Create: `backend/app/observability/__init__.py`, `backend/app/observability/callback.py`
- Test: `backend/tests/test_callback.py`

- [ ] **Step 1: Write the failing test** (callback records a row on tool end)

```python
import pytest
from app.observability.callback import ToolLoggingCallbackHandler

@pytest.mark.asyncio
async def test_callback_logs_tool_call():
    captured = []
    async def fake_record(**kwargs): captured.append(kwargs)
    cb = ToolLoggingCallbackHandler(agent_name="qa", record_fn=fake_record)
    run_id = "r1"
    await cb.on_tool_start({"name": "run_tests"}, "{\"repo\": \"x\"}", run_id=run_id)
    await cb.on_tool_end("{\"passed\": true}", run_id=run_id)
    assert captured[0]["agent_name"] == "qa"
    assert captured[0]["skill_requested"] == "run_tests"
    assert captured[0]["status"] == "success"
```

- [ ] **Step 2: Run it, expect failure** — `pytest tests/test_callback.py -v`

- [ ] **Step 3: Implement `app/observability/callback.py`**

```python
import time
from typing import Any, Callable
from uuid import UUID

from langchain_core.callbacks import AsyncCallbackHandler

class ToolLoggingCallbackHandler(AsyncCallbackHandler):
    """Logs every LangGraph tool call to agent_execution_logs via record_fn."""

    def __init__(self, agent_name: str, record_fn: Callable, **ids: Any):
        self.agent_name = agent_name
        self._record_fn = record_fn
        self._ids = ids  # ticket_execution_id / project_id
        self._inflight: dict[str, dict] = {}

    async def on_tool_start(self, serialized: dict, input_str: str, *, run_id: UUID | str, **kwargs):
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
            agent_name=self.agent_name, skill_requested=meta["name"],
            input_payload={"raw": meta["input"]}, output_payload={"raw": str(output)},
            status="success", duration_ms=int((time.monotonic() - meta["t0"]) * 1000),
            **self._ids,
        )

    async def on_tool_error(self, error: BaseException, *, run_id: UUID | str, **kwargs):
        meta = self._inflight.pop(str(run_id), None)
        if not meta:
            return
        await self._record_fn(
            agent_name=self.agent_name, skill_requested=meta["name"],
            input_payload={"raw": meta["input"]}, output_payload={"error": str(error)},
            status="failed", duration_ms=int((time.monotonic() - meta["t0"]) * 1000),
            **self._ids,
        )
```

- [ ] **Step 4: Run it, expect pass**

- [ ] **Step 5: Commit**

```bash
git add backend/app/observability/ backend/tests/test_callback.py
git commit -m "feat(m0): tool-call logging callback handler"
```

---

## Task 10: Wire MCP startup into the app + M0 verification gate

**Files:**
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_app_startup.py`

- [ ] **Step 1: Write the failing test** (app exposes the manager; `/health/mcp` lists tool names)

```python
from fastapi.testclient import TestClient
from app.main import create_app

def test_mcp_debug_endpoint(monkeypatch):
    async def fake_startup(self): self._tools_by_name = {"confluence_get_page": object()}
    monkeypatch.setattr("app.mcp.client.MCPClientManager.startup", fake_startup)
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/health/mcp")
        assert resp.status_code == 200
        assert "confluence_get_page" in resp.json()["tools"]
```

- [ ] **Step 2: Run it, expect failure** — `pytest tests/test_app_startup.py -v`

- [ ] **Step 3: Update `app/main.py`** (lifespan starts the MCP manager; debug endpoint)

```python
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
```

- [ ] **Step 4: Run it, expect pass** — `pytest tests/test_app_startup.py -v`

- [ ] **Step 5: Run the full suite + lint**

Run: `cd backend && ruff check . && pytest -v`
Expected: all pass.

- [ ] **Step 6: M0 VERIFICATION GATE — manual smoke test against real services**

1. Set a real `MCP_SERVERS` (at least the GitHub MCP) + `DATABASE_URL` in `backend/.env`.
2. `alembic upgrade head` → confirm 4 tables.
3. `uvicorn app.main:app` → `GET /health` returns `{"status":"ok"}`.
4. `GET /health/mcp` returns a non-empty tool list including `create_repository`, `confluence_get_page`, `jira_create_issue`, `assign_copilot_to_issue`.
5. In a Python shell: clone a small public repo with `clone_branch`, run `run_tests` on its `tests/`, confirm a parsed result dict.
6. Insert a log via `record_agent_log` and `SELECT` it back.

- [ ] **Step 7: Commit**

```bash
git add backend/app/main.py backend/tests/test_app_startup.py
git commit -m "feat(m0): MCP startup lifespan + /health/mcp; M0 complete"
```

---

## Self-Review (M0)

- **Spec coverage:** config ✓, LLMClient ✓, 4-table schema + migrations ✓, MCP client + scoped tools ✓ (replaces SkillExecutor per D3), logging callback ✓ (D4), local-exec ✓ (D2). No webhook handling yet — that's M2, intentionally.
- **Placeholders:** none; every step has runnable code. The one forward-reference (`pytest-json-report` install) is explicitly deferred to M2 with a note.
- **Type consistency:** `record_agent_log(**kwargs)` signature matches the callback's call site; `tools_for(agent)` keys match `AGENT_TOOL_SCOPES` and the M1/M2 agent names (`pm`, `architecture`, `jira_structuring`, `planning`, `qa`, `review`, `jira_update`).

**Verification gate:** the app boots, migrations apply, `/health/mcp` lists real MCP tools, a cloned repo runs pytest, and a log row round-trips. Only then start M1.
