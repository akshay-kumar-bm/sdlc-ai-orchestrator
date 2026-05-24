# AEO — Implementation Specification
### AI Engineering Orchestrator | Full MVP Build Spec | v1.2

> **v1.2 supersedes parts of this file.** See `docs/superpowers/specs/2026-05-24-aeo-architecture-decisions.md` for the authoritative deltas. In short: (1) connect to **existing** Confluence/Jira/GitHub MCP servers — do not build custom integration servers; (2) **no central `SkillExecutor`** — agents bind a scoped subset of MCP tools, with a logging callback for observability; (3) Architecture + Repo Bootstrap are **one** agent (7 agents total).

---

## Finalized Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Repo structure | Monorepo | Single repo for /backend, /frontend, /agents (no /mcp-servers — see below) |
| Agent framework | LangGraph | Native state graphs, tool calling, conditional retry edges |
| LLM provider | Flexible (Anthropic / OpenAI) | Abstract `LLMClient` — swap per agent or per deployment |
| **Integration layer** | **Existing MCP servers** | Connect as an MCP client (`langchain-mcp-adapters`) to the already-configured Confluence/Jira/GitHub MCP servers. We do **not** build or run integration servers. |
| **Tool governance** | **Scoped per-agent toolsets** | Each agent is bound only the MCP tools it needs. Replaces the central `SkillExecutor`. Observability via a LangGraph callback → `agent_execution_logs`. |
| **Code authoring** | **GitHub Copilot** | Planning Agent creates a detailed issue and assigns Copilot — Copilot writes all code autonomously |
| Test execution | Direct subprocess (in-process, ours) | The only integration we own: clone + pytest/ruff on the cloned repo. No server. |
| Frontend auth | None (MVP) | Single-user internal dashboard |
| State store | Supabase (PostgreSQL) | Relational state tracking, free tier |

---

## 1. Monorepo Structure

```
sdlc-ai-orchestrator/
├── backend/                   # FastAPI orchestrator
│   ├── app/
│   │   ├── api/               # Webhook endpoints
│   │   ├── agents/            # LangGraph agent definitions
│   │   ├── core/              # Config, LLM client abstraction
│   │   ├── db/                # Supabase client, models
│   │   ├── orchestrator/      # State machine, dispatcher, retry logic
│   │   ├── mcp/               # MCP client manager + per-agent scoped toolsets
│   │   ├── local_exec/        # The only integration we own: clone + pytest + ruff
│   │   └── main.py
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                  # Next.js dashboard
│   ├── src/
│   │   ├── app/               # Next.js 14 app router
│   │   ├── components/        # Chat, approval views, monitor
│   │   └── lib/               # API client to backend
│   └── package.json
│                              # NOTE (v1.2): no /mcp-servers — we connect to existing
│                              # Confluence/Jira/GitHub MCP servers as a client.
├── agents/                    # Claude Code agent definitions (existing)
│   ├── product-manager.md
│   ├── solution-architecture.md
│   ├── tech-lead-breakdown.md
│   └── agent-architect.md
├── docker-compose.yml         # Local dev: backend + frontend
├── CLAUDE.md
├── IMPLEMENTATION_SPEC.md     # This file
└── project_detail.md          # Source of truth for system design
```

---

## 2. Technology Stack

| Layer | Technology | Version |
|---|---|---|
| Backend framework | FastAPI | 0.111+ |
| Agent framework | LangGraph | 0.2+ |
| LLM SDK (Anthropic) | anthropic | 0.30+ |
| LLM SDK (OpenAI) | openai | 1.40+ |
| State DB | Supabase / PostgreSQL | Latest |
| ORM | SQLAlchemy 2.0 async | 2.0+ |
| DB migrations | Alembic | Latest |
| Frontend | Next.js (TypeScript) | 14 (App Router) |
| Frontend state | Zustand | Latest |
| Python version | 3.11 | — |
| Node version | 20 LTS | — |

---

## 3. Local Development Setup

### Prerequisites
- Docker + Docker Compose
- Python 3.11
- Node 20 LTS
- Supabase account (free tier)
- Atlassian Cloud account (Confluence + Jira)
- GitHub personal access token

### Environment Variables

```bash
# backend/.env
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...           # Optional — only if using OpenAI
LLM_PROVIDER=anthropic       # "anthropic" | "openai"
LLM_MODEL=claude-sonnet-4-6  # or "gpt-4o"

SUPABASE_URL=...
SUPABASE_ANON_KEY=...
DATABASE_URL=postgresql+asyncpg://...

CONFLUENCE_BASE_URL=https://your-org.atlassian.net/wiki
CONFLUENCE_API_TOKEN=...
CONFLUENCE_EMAIL=...
JIRA_BASE_URL=https://your-org.atlassian.net
JIRA_API_TOKEN=...
JIRA_EMAIL=...

GITHUB_PAT=...
GITHUB_DEFAULT_ORG=...

WEBHOOK_SECRET=...           # HMAC secret for Jira/GitHub webhooks
```

### docker-compose.yml (local dev)

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: ./backend/.env
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --reload --host 0.0.0.0

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    volumes:
      - ./frontend:/app
    command: npm run dev
```

---

## 4. LLM Provider Abstraction

All agents receive an `LLMClient` instance — never instantiate a provider SDK directly in agent code.

```python
# backend/app/core/llm_client.py

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from app.core.config import settings

def get_llm(model_override: str | None = None):
    model = model_override or settings.LLM_MODEL
    if settings.LLM_PROVIDER == "anthropic":
        return ChatAnthropic(model=model, api_key=settings.ANTHROPIC_API_KEY)
    return ChatOpenAI(model=model, api_key=settings.OPENAI_API_KEY)
```

**Model selection per agent:**

| Agent | Default Model | Reason |
|---|---|---|
| PM Agent | sonnet | Conversational reasoning |
| Architecture Agent | opus | Complex technical decisions |
| Repo Bootstrap Agent | haiku | Deterministic, no heavy reasoning |
| Jira Structuring Agent | sonnet | Structured output generation |
| Planning Agent | sonnet | Repo analysis + plan generation |
| Dev Agent | — | **GitHub Copilot** (no AEO LLM cost) |
| QA Agent | sonnet | Test log parsing + error report generation |
| Review Agent | sonnet | Acceptance criteria comparison |
| Jira Update Agent | haiku | Simple structured writes |

---

## 5. Database Schema (Supabase / PostgreSQL)

```sql
-- Run via Alembic migrations

CREATE TABLE projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'INITIALIZED',
    -- status: INITIALIZED | PRD_DRAFTING | PRD_APPROVED | ARCHITECTURE_DESIGN
    --         | ARCHITECTURE_APPROVED | REPO_BOOTSTRAPPING | JIRA_STRUCTURING
    --         | EPICS_PENDING_APPROVAL | STORIES_GENERATING | PHASE_1_COMPLETE
    confluence_prd_url      TEXT,
    confluence_arch_url     TEXT,
    github_repo_url         TEXT,
    jira_project_key        VARCHAR(50),
    confluence_space_key    VARCHAR(50),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE ticket_executions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID REFERENCES projects(id),
    jira_ticket_key VARCHAR(50) NOT NULL,
    github_issue_url        TEXT,
    github_pr_url           TEXT,
    github_branch           TEXT,
    status          VARCHAR(50) NOT NULL DEFAULT 'AI_READY',
    -- status: AI_READY | PLANNING | IN_DEVELOPMENT | IN_QA
    --         | FIXING | READY_TO_MERGE | MERGED | JIRA_UPDATED | ESCALATED
    retry_count     INTEGER DEFAULT 0,
    current_agent   VARCHAR(100),
    last_error      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE agent_execution_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_execution_id UUID REFERENCES ticket_executions(id),
    project_id          UUID REFERENCES projects(id),
    agent_name          VARCHAR(100) NOT NULL,
    skill_requested     VARCHAR(100),
    input_payload       JSONB,
    output_payload      JSONB,
    status              VARCHAR(50),  -- success | failed | retrying
    token_usage         INTEGER,
    duration_ms         INTEGER,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE human_approval_requests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID REFERENCES projects(id),
    approval_type   VARCHAR(100) NOT NULL,
    -- approval_type: PRD | ARCHITECTURE | EPICS | STORIES | ESCALATION
    payload         JSONB NOT NULL,   -- the content to approve
    status          VARCHAR(50) DEFAULT 'PENDING',  -- PENDING | APPROVED | REJECTED
    feedback        TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_ticket_executions_status ON ticket_executions(status);
CREATE INDEX idx_ticket_executions_project ON ticket_executions(project_id);
CREATE INDEX idx_agent_logs_ticket ON agent_execution_logs(ticket_execution_id);
```

---

## 6. FastAPI Backend — Core Modules

### 6.1 Orchestrator State Machine

```python
# backend/app/orchestrator/state_machine.py

# Allowed transitions — the orchestrator enforces these; no agent can bypass
TICKET_TRANSITIONS = {
    "AI_READY":           ["PLANNING"],
    "PLANNING":           ["COPILOT_ASSIGNED"],   # Planning Agent assigns Copilot
    "COPILOT_ASSIGNED":   ["IN_QA"],              # Copilot opens PR → triggers QA
    "IN_QA":              ["READY_TO_MERGE", "COPILOT_RETRY", "ESCALATED"],
    "COPILOT_RETRY":      ["IN_QA", "ESCALATED"], # Re-assign Copilot with error context
    "READY_TO_MERGE":     ["MERGED"],
    "MERGED":             ["JIRA_UPDATED"],
}

PROJECT_TRANSITIONS = {
    "INITIALIZED":              ["PRD_DRAFTING"],
    "PRD_DRAFTING":             ["PRD_APPROVED"],
    "PRD_APPROVED":             ["ARCHITECTURE_DESIGN"],
    "ARCHITECTURE_DESIGN":      ["ARCHITECTURE_APPROVED"],
    "ARCHITECTURE_APPROVED":    ["REPO_BOOTSTRAPPING", "JIRA_STRUCTURING"],
    "REPO_BOOTSTRAPPING":       ["PHASE_1_COMPLETE"],  # after Jira also done
    "JIRA_STRUCTURING":         ["EPICS_PENDING_APPROVAL"],
    "EPICS_PENDING_APPROVAL":   ["STORIES_GENERATING"],
    "STORIES_GENERATING":       ["PHASE_1_COMPLETE"],
}
```

### 6.2 Webhook Endpoints

```python
# backend/app/api/webhooks.py

POST /webhooks/jira     # Jira issue status change events
POST /webhooks/github   # GitHub PR opened, CI status, PR merged

# Event → Agent routing (handled by dispatcher):
# jira:issue_status_changed → AI_READY  → Planning Agent (creates issue + assigns Copilot)
# github:pr_opened          → QA Agent  (Copilot opened the PR)
# github:ci_passed          → Review Agent
# github:pr_merged          → Jira Update Agent
# github:ci_failed          → Re-assign Copilot with QA error context (retry_count < 3)
# github:ci_failed (retry=3)→ ESCALATED → human_approval_request
```

### 6.3 Human Approval Endpoints

```python
# backend/app/api/approvals.py

GET  /approvals/{project_id}/pending        # List pending approvals
POST /approvals/{approval_id}/approve       # Approve with optional feedback
POST /approvals/{approval_id}/reject        # Reject with required feedback
```

### 6.4 Project Initialization Endpoints

```python
# backend/app/api/projects.py

POST /projects                     # Create new project, start Phase 1
GET  /projects/{id}                # Project state + links
GET  /projects/{id}/executions     # All ticket executions for this project
POST /projects/{id}/chat           # Send message to PM Agent (Phase 1 chat)
```

### 6.5 Tool Governance (v1.2 — replaces the `SkillExecutor`)

Agents bind a **scoped subset of MCP tools** (loaded from the existing MCP servers via `langchain-mcp-adapters`). There is no central skill registry. Governance is achieved by:

1. **Scoping** — each agent receives only the tools in its row of the per-agent tool matrix (see the architecture-decisions doc). The MCP client manager exposes a `tools_for(agent_name)` helper.
2. **Observability** — a LangGraph `BaseCallbackHandler` records every tool call (agent, tool, input, output, token usage, duration, status) to `agent_execution_logs`.
3. **Constraint enforcement** — because Copilot writes code autonomously, architecture-constraint checks happen post-hoc in the Review Agent, not via pre-commit interception.

The tool surface below is now **provided by the existing MCP servers**, not implemented by us. It is retained here only as a reference of the tools agents draw from. The one exception — `clone_branch`, `run_tests`, `run_linter`, `parse_test_logs` — is our in-process `local_exec` module.

```python
# Reference only — these are MCP-server tools, not a registry we build.
MCP_TOOL_SURFACE = {
    # GitHub
    "create_github_branch":  github_skills.create_branch,
    "read_github_file":      github_skills.read_file,
    "commit_files":          github_skills.commit_files,
    "open_pull_request":     github_skills.open_pr,
    "merge_pull_request":    github_skills.merge_pr,
    "get_repo_tree":         github_skills.get_file_tree,
    "comment_on_pr":         github_skills.comment_on_pr,
    "get_pr_diff":           github_skills.get_pr_diff,
    "get_ci_status":         github_skills.get_ci_status,
    "create_github_issue":       github_skills.create_issue,
    "assign_copilot_to_issue":   github_skills.assign_copilot,      # triggers Copilot to code
    "get_copilot_job_status":    github_skills.copilot_job_status,   # poll until PR opened
    # Jira
    "fetch_jira_issue":      jira_skills.fetch_issue,
    "create_epic":           jira_skills.create_epic,
    "create_story":          jira_skills.create_story,
    "update_ticket_status":  jira_skills.update_status,
    "add_jira_comment":      jira_skills.add_comment,
    # Confluence
    "fetch_confluence_page": confluence_skills.fetch_page,
    "create_confluence_page":confluence_skills.create_page,
    "update_confluence_page":confluence_skills.update_page,
    # Local Execution
    "run_tests":             local_skills.run_tests,
    "run_linter":            local_skills.run_linter,
    "format_code":           local_skills.format_code,
    "parse_test_logs":       local_skills.parse_logs,
    "clone_branch":          local_skills.clone_branch,
}
```

---

## 7. Integration Layer (v1.2 — existing MCP servers, not custom builds)

We **connect** to the Confluence, Jira, and GitHub MCP servers already configured in this environment. We do not implement or run them. The backend uses `langchain-mcp-adapters` `MultiServerMCPClient` to load their tools and bind scoped subsets per agent. Connection details (remote URLs or stdio launch commands) + tokens come from the `MCP_SERVERS` config (see M0 plan).

### 7.1 Confluence MCP (existing)

Tools used: `confluence_search`, `confluence_get_page`, `confluence_get_page_children`, `confluence_create_page`, `confluence_update_page`, `confluence_add_comment`, `confluence_add_label`.

### 7.2 Jira MCP (existing)

Tools used: `jira_list_projects`, `jira_get_project`, `jira_get_field_options`, `jira_get_issue`, `jira_create_issue`, `jira_update_issue`, `jira_add_comment`, `jira_get_transitions`, `jira_transition_issue`, `jira_get_issue_link_types`.

**Constraints:** no sub-task `parent` field (use issue type **Task**, link via comment); no `create_issue_link` (document dependencies via comments).

### 7.3 GitHub MCP (existing)

Tools used: `get_me`, `create_repository`, `create_branch`, `list_branches`, `get_file_contents`, `push_files`, `create_or_update_file`, `issue_write`, `assign_copilot_to_issue`, `get_copilot_job_status`, `pull_request_read`, `pull_request_review_write`, `request_copilot_review`, `merge_pull_request`, `add_issue_comment`.

### 7.4 Local Execution (`backend/app/local_exec/` — the one integration we own)

Runs directly via subprocess. No Docker for MVP.

```python
# mcp-servers/local-execution/server.py

async def run_tests(repo_path: str, test_path: str = "tests/") -> dict:
    result = subprocess.run(
        ["pytest", test_path, "--json-report", "--json-report-file=/tmp/report.json"],
        cwd=repo_path, capture_output=True, text=True, timeout=300
    )
    return parse_json_report("/tmp/report.json")

async def run_linter(repo_path: str) -> dict:
    result = subprocess.run(
        ["ruff", "check", ".", "--output-format=json"],
        cwd=repo_path, capture_output=True, text=True
    )
    return json.loads(result.stdout)

async def clone_branch(repo_url: str, branch: str, target_dir: str) -> dict:
    subprocess.run(["git", "clone", "-b", branch, repo_url, target_dir], check=True)
    return {"path": target_dir}
```

---

## 8. Agent Implementations (LangGraph)

Each agent is a LangGraph `StateGraph`. All use the `LLMClient` abstraction. All skill calls go through `SkillExecutor`.

---

### 8.1 PM Agent (Phase 1)

**Graph:** `chat_loop → draft_prd → save_to_confluence → request_approval → [approved → done | rejected → chat_loop]`

**State:**
```python
class PMAgentState(TypedDict):
    project_id: str
    messages: list[BaseMessage]    # full conversation history
    prd_draft: str
    confluence_page_id: str | None
    approval_status: str           # PENDING | APPROVED | REJECTED
```

**Key behaviors:**
- Maintains full conversation history across turns
- Proactively asks about NFRs, compliance, scale if not mentioned
- Only calls `save_to_confluence` when draft is complete (user confirms)
- Emits `human_approval_request` record; waits for `POST /approvals/{id}/approve`

---

### 8.2 Architecture Agent (Phase 1)

**Graph:** `read_prd → propose_stack → await_stack_approval → propose_schema → await_schema_approval → write_arch_plan → request_final_approval`

**State:**
```python
class ArchAgentState(TypedDict):
    project_id: str
    prd_content: str
    proposed_stack: dict
    proposed_schema: dict
    folder_structure: str
    confluence_arch_page_id: str | None
    approval_checkpoints: list[dict]
```

**Constraint enforced:** Architecture plan saved to Confluence becomes the immutable reference for all Phase 2 agents. Dev Agent reads it on every execution.

---

### 8.3 Repo Bootstrap (v1.2 — merged into the Architecture Agent §8.2)

This is **no longer a separate agent.** After the human approves the architecture plan, the Architecture Agent itself creates the repo and injects `docs/ARCHITECTURE.md` + README + skeleton (via `create_repository`, `push_files`). The steps below describe that repo-provisioning behavior, now owned by §8.2.

**Deterministic — minimal LLM use.** Reads the approved architecture plan and generates files.

**Steps (sequential):**
1. `fetch_confluence_page` (architecture plan)
2. Parse tech stack, folder structure
3. Generate all template files (main.py, requirements.txt, Dockerfile, ci.yml, README.md)
4. `create_github_branch` (main)
5. `commit_files` (all templates in one commit)
6. `create_github_issue` ("Project initialized by AEO")

**No retry logic** — deterministic operations; surface errors immediately.

---

### 8.4 Jira Structuring Agent (Phase 1)

**Two sub-graphs run in sequence:** Epic Generator → (await Epic approval) → Story Generator

**Epic Generator:**
- Reads PRD from Confluence
- Groups features into 3–7 functional epics
- Creates `human_approval_request` with epic list
- On approval: calls `create_epic` for each

**Story Generator (per epic):**
- Reads architecture plan for technical notes
- Generates 3–6 stories per epic in Given/When/Then format
- Calls `create_story` with acceptance criteria and technical notes

---

### 8.5 Planning Agent (Phase 2)

**Trigger:** Jira ticket moves to `AI_READY`

**Graph:** `fetch_jira_ticket → fetch_arch_plan → analyze_repo_tree → build_plan → create_github_issue → assign_copilot_to_issue → poll_until_pr_opened`

**This is the most critical Phase 2 agent.** Its GitHub Issue is the sole input Copilot works from — it must be unambiguous and complete.

**State:**
```python
class PlanningAgentState(TypedDict):
    ticket_execution_id: str
    jira_ticket_key: str
    arch_plan: str
    repo_tree: list[str]
    github_issue_url: str | None
    copilot_job_id: str | None
    pr_url: str | None
```

**GitHub Issue format (Copilot-optimised):**
```markdown
## Task: {jira_title}

**Jira:** {ticket_key} | **Epic:** {epic_key}
**Branch to create:** `feature/{ticket_key}-{slug}`

---

### Context
{2-3 sentences on what this feature does and why, taken from Jira description}

### Architecture Constraints
- Tech stack: {from arch plan}
- Must not create new top-level directories
- Must not change requirements.txt unless listed below
- Follow existing naming and folder conventions (see repo tree below)

### Current Repo Structure (relevant paths)
```
{filtered repo tree — only paths relevant to this ticket}
```

### Files to Create or Modify
| File | Action | What to implement |
|---|---|---|
| `app/api/v1/routes/auth.py` | modify | Add POST /auth/register endpoint |
| `app/models/user.py` | create | SQLAlchemy User model with fields: id, email, hashed_password, created_at |
| `app/schemas/user.py` | create | Pydantic UserCreate, UserResponse schemas |
| `app/services/auth_service.py` | create | register() method: validate email uniqueness, hash password with bcrypt, return JWT |
| `tests/unit/test_auth_service.py` | create | Unit tests for register() — happy path + duplicate email |
| `tests/integration/test_auth_routes.py` | create | Integration tests for POST /auth/register |

### Database Changes
{Alembic migration details if needed, or "None"}

### API Contract
```
POST /auth/register
Request:  { "email": string, "password": string }
Response 201: { "access_token": string, "token_type": "bearer" }
Response 409: { "detail": "Email already registered" }
Response 422: validation error
```

### Acceptance Criteria (must all pass)
- [ ] Given valid email+password → returns 201 with JWT
- [ ] Given duplicate email → returns 409
- [ ] Password stored as bcrypt hash (never plaintext)
- [ ] Unit tests pass: pytest tests/unit/test_auth_service.py
- [ ] Integration tests pass: pytest tests/integration/test_auth_routes.py
- [ ] ruff check passes with no violations

### Dependencies / Libraries
- `passlib[bcrypt]` (already in requirements.txt)
- `python-jose` (already in requirements.txt)
- Follow pattern in `app/services/existing_service.py` for service structure
```

**After issue is created:** calls `assign_copilot_to_issue` → Copilot autonomously creates the branch, writes all files, and opens a PR. The orchestrator polls `get_copilot_job_status` until PR is opened, then transitions ticket to `IN_QA`.

**Constraint:** All file paths in the issue must exist in the approved architecture folder structure.

---

### 8.6 GitHub Copilot (Code Authoring)

**Not an AEO agent — this is GitHub Copilot operating natively.**

Copilot receives the Planning Agent's GitHub Issue via `assign_copilot_to_issue` and autonomously:
1. Creates the feature branch (`feature/{ticket_key}-{slug}`)
2. Writes all specified files per the issue instructions
3. Opens a Pull Request linked to the issue

**AEO's role during this step:** passive — the orchestrator polls `get_copilot_job_status` and waits for the `github:pr_opened` webhook event before advancing the state machine.

**No AEO code to write for this step** beyond the two skill wrappers (`assign_copilot_to_issue`, `get_copilot_job_status`).

---

### 8.7 QA Agent (Phase 2)

**Trigger:** PR opened by Copilot (`github:pr_opened` webhook)

**Graph:** `read_pr_diff → read_acceptance_criteria → clone_branch → run_linter → run_tests → evaluate_results → [pass → post_results | fail → build_error_report → re_assign_copilot]`

**On failure:**
```python
error_report = {
    "failing_tests": [...],
    "lint_violations": [...],
    "root_cause_hypothesis": "...",    # LLM-generated
    "suggested_fix": "...",            # specific guidance for Copilot retry
}
```

**On retry:** The orchestrator updates the GitHub Issue with a new comment containing the structured error report, then calls `assign_copilot_to_issue` again on the same issue. Copilot pushes a fix commit to the existing branch.

If `retry_count < 3`: add error comment to issue, re-assign Copilot, transition to `COPILOT_RETRY`.
If `retry_count == 3`: transition to `ESCALATED`, create `human_approval_request` with full failure log.

---

### 8.8 Review Agent (Phase 2)

**Trigger:** QA Agent marks all tests and lint as passed

**Graph:** `read_pr_diff → fetch_jira_acceptance_criteria → fetch_arch_plan → run_checklist → [all_pass → approve_pr | issues → request_changes]`

**Checklist items evaluated:**
1. Acceptance criteria coverage (Jira Given/When/Then)
2. Architecture compliance (no boundary violations)
3. No hardcoded secrets or credentials
4. No dead code introduced
5. PR description references Jira ticket

**On approval:** calls `merge_pull_request` skill.

---

### 8.9 Jira Update Agent (Phase 2)

**Trigger:** PR merged

**Graph:** `fetch_execution_record → transition_jira_to_done → add_jira_comment`

**Jira comment posted:**
```
✅ AEO — Automated Update
PR Merged: {pr_url}
Branch: {branch_name}
Tests: {test_count} passing | CI: ✅
Cycle time: {duration} from AI Ready → Merged
```

---

## 9. Next.js Frontend

### Pages

| Route | Purpose |
|---|---|
| `/` | Project list + create new project |
| `/projects/[id]` | Project dashboard: status, links, execution monitor |
| `/projects/[id]/chat` | PM Agent chat interface (Phase 1) |
| `/projects/[id]/approve/[approval_id]` | Human approval view |
| `/projects/[id]/tickets` | Ticket execution list with state |
| `/projects/[id]/tickets/[execution_id]` | Ticket detail: agent logs, retry history |

### Key Components

- **`<ChatInterface>`** — Streaming message display + input box for PM Agent
- **`<ApprovalCard>`** — Renders PRD/Architecture/Epic/Story for human review with Approve/Reject + feedback
- **`<ExecutionMonitor>`** — Live-polling table of ticket states, current agent, retry count
- **`<AgentLogViewer>`** — Expandable log per agent execution with token usage and duration

### API Client

```typescript
// frontend/src/lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL;

export const api = {
  sendChatMessage: (projectId: string, message: string) =>
    fetch(`${API_BASE}/projects/${projectId}/chat`, { method: "POST", body: JSON.stringify({ message }) }),
  approveRequest: (approvalId: string, feedback?: string) =>
    fetch(`${API_BASE}/approvals/${approvalId}/approve`, { method: "POST", body: JSON.stringify({ feedback }) }),
  getPendingApprovals: (projectId: string) =>
    fetch(`${API_BASE}/approvals/${projectId}/pending`),
  getExecutions: (projectId: string) =>
    fetch(`${API_BASE}/projects/${projectId}/executions`),
};
```

---

## 10. Build Order (30-Day MVP)

### Week 1 — Foundation
- [ ] Monorepo scaffold (`/backend`, `/frontend`, `/mcp-servers`)
- [ ] FastAPI app skeleton with config, DB connection, Alembic migrations
- [ ] Supabase schema (all 4 tables)
- [ ] `LLMClient` abstraction (Anthropic + OpenAI)
- [ ] `SkillExecutor` with registry + logging
- [ ] Confluence MCP server (fetch, create, update)
- [ ] Jira MCP server (fetch, create epic/story, transition, comment)
- [ ] Webhook signature validation middleware

### Week 2 — Phase 1 Agents
- [ ] PM Agent (LangGraph, Confluence tools, approval gate)
- [ ] Architecture Agent (multi-checkpoint approval flow)
- [ ] Repo Bootstrap Agent (file generation + GitHub skills)
- [ ] Jira Structuring Agent (Epic + Story sub-graphs)
- [ ] Project state machine + `POST /projects` endpoint
- [ ] Human approval endpoints (`/approvals/*`)

### Week 3 — Phase 2 Agents
- [ ] Local Execution MCP (clone, pytest, ruff, log parsing)
- [ ] `assign_copilot_to_issue` + `get_copilot_job_status` skill wrappers
- [ ] Planning Agent (rich GitHub Issue generation + Copilot assignment)
- [ ] QA Agent (PR diff read, subprocess test run, error report, Copilot retry)
- [ ] Review Agent (acceptance criteria checklist + PR merge)
- [ ] Jira Update Agent (status + comment)
- [ ] Webhook handlers (Jira AI_READY, GitHub PR opened/merged/CI)
- [ ] Ticket state machine with `COPILOT_ASSIGNED → IN_QA → COPILOT_RETRY` transitions + retry cap

### Week 4 — Frontend + Integration
- [ ] Next.js project scaffold (App Router, TypeScript)
- [ ] Chat interface for PM Agent
- [ ] Approval views (PRD, Architecture, Epics, Stories)
- [ ] Execution monitor (polling `/projects/{id}/executions`)
- [ ] Agent log viewer
- [ ] End-to-end test: idea → PR merged → Jira Done
- [ ] Fix bugs, clean up error paths, document env setup

---

## 11. Success Criteria (Definition of Done)

The MVP is complete when a live end-to-end demo runs without human intervention beyond the defined approval gates:

1. User types a product idea in the chat interface
2. PM Agent generates and saves a PRD to real Confluence
3. Human approves PRD in dashboard
4. Architecture Agent produces architecture plan in Confluence
5. Human approves architecture
6. Repo Bootstrap Agent creates a real GitHub repo with base skeleton
7. Jira Structuring Agent creates Epics and Stories in real Jira
8. Human approves Epics and Stories
9. Human moves one Jira Story to "AI Ready"
10. Planning Agent creates a detailed GitHub Issue and assigns GitHub Copilot to it
11. GitHub Copilot autonomously creates a branch, writes code, and opens a PR
12. QA Agent clones the branch, runs pytest + ruff, posts results as PR comment
13. Review Agent checks acceptance criteria and merges the PR
14. Jira Update Agent moves ticket to Done and posts PR link
15. Execution monitor shows the full ticket lifecycle with correct state transitions

**Metrics to capture on demo run:**
- Total cycle time: AI Ready → Merged
- Retry count for the demo ticket
- Token usage per agent
- All 4 Confluence + Jira + GitHub links populated in DB

---

## 12. Out of Scope (MVP)

- Frontend UI code generation
- Multi-repo / microservices projects
- Cloud deployment automation (AWS/GCP)
- Slack/Teams notifications
- SOC2 / compliance tooling
- Vector memory (Chroma / pgvector) — architecture memory is fetched fresh each time
- Cost monitoring dashboard

---

*Spec version: 1.1 | Updated: May 2026 | Project: AEO*
*Change in v1.1: Dev Agent replaced by GitHub Copilot. Planning Agent now owns issue creation + Copilot assignment. QA retry re-assigns Copilot with error context.*
