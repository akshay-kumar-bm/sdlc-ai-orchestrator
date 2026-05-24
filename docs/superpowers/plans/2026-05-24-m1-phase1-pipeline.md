# M1 — Phase 1 Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: re-run superpowers:writing-plans to expand this roadmap into bite-sized TDD steps **immediately before building**, then use superpowers:subagent-driven-development. This document is a concrete, reviewable roadmap (file maps + interfaces + key code + test names + verification gates), refined to micro-steps at execution time per decision **D8**.

**Goal:** Drive a project from an idea to a live GitHub repo + Confluence PRD/architecture + a Jira backlog, gated by human approvals — using the three Phase 1 agents on the M0 foundation.

**Architecture:** A project advances through `PROJECT_TRANSITIONS` (state machine). API endpoints create projects, relay chat to the PM Agent, and resolve approvals. Each agent is a LangGraph `StateGraph` that gets its LLM from `get_llm()` and its tools from `MCPClientManager.tools_for(<agent>)`, with the `ToolLoggingCallbackHandler` attached. Approvals are persisted as `human_approval_requests`; an agent pauses until the matching approval is resolved.

**Tech Stack:** Same as M0 + LangGraph state graphs. No new external deps.

**Depends on:** M0 complete (config, DB, MCP client, callback, local-exec).

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/app/orchestrator/project_states.py` | `PROJECT_TRANSITIONS`, `can_transition`, `assert_transition` |
| `backend/app/orchestrator/projects.py` | `ProjectService`: create, get, advance state |
| `backend/app/orchestrator/approvals.py` | `ApprovalService`: create/approve/reject; `await_approval` |
| `backend/app/orchestrator/dispatcher.py` | Maps project state → next agent; runs the agent |
| `backend/app/agents/base.py` | `build_agent(name, system_prompt, mcp)` → bound LangGraph ReAct graph |
| `backend/app/agents/pm.py` | PM Agent graph + system prompt |
| `backend/app/agents/architecture.py` | Architecture Agent graph (design + repo provision) |
| `backend/app/agents/jira_structuring.py` | Epic + Story sub-graphs |
| `backend/app/api/projects.py` | `POST /projects`, `GET /projects/{id}`, `/executions`, `POST /chat` |
| `backend/app/api/approvals.py` | `GET /approvals/{project_id}/pending`, approve, reject |
| `backend/app/schemas/*.py` | Pydantic request/response + agent state TypedDicts |
| `backend/tests/...` | Per-module tests + a Phase-1 integration test |

---

## Task 1: Project state machine

**Files:** Create `app/orchestrator/project_states.py`; Test `tests/test_project_states.py`

Implement the transition table from the spec and a guard:

```python
PROJECT_TRANSITIONS: dict[str, list[str]] = {
    "INITIALIZED": ["PRD_DRAFTING"],
    "PRD_DRAFTING": ["PRD_APPROVED"],
    "PRD_APPROVED": ["ARCHITECTURE_DESIGN"],
    "ARCHITECTURE_DESIGN": ["ARCHITECTURE_APPROVED"],
    "ARCHITECTURE_APPROVED": ["REPO_BOOTSTRAPPING", "JIRA_STRUCTURING"],
    "REPO_BOOTSTRAPPING": ["PHASE_1_COMPLETE"],
    "JIRA_STRUCTURING": ["EPICS_PENDING_APPROVAL"],
    "EPICS_PENDING_APPROVAL": ["STORIES_GENERATING"],
    "STORIES_GENERATING": ["PHASE_1_COMPLETE"],
}

class InvalidTransition(Exception): ...

def can_transition(src: str, dst: str) -> bool:
    return dst in PROJECT_TRANSITIONS.get(src, [])

def assert_transition(src: str, dst: str) -> None:
    if not can_transition(src, dst):
        raise InvalidTransition(f"{src} -> {dst} not allowed")
```

**Tests:** `test_valid_transition_passes`, `test_invalid_transition_raises`, `test_terminal_state_has_no_transitions`.
**Commit:** `feat(m1): project state machine`

---

## Task 2: ProjectService

**Files:** Create `app/orchestrator/projects.py`, `app/schemas/project.py`; Test `tests/test_project_service.py`

Interface:

```python
class ProjectService:
    def __init__(self, session: AsyncSession): ...
    async def create(self, name: str, confluence_space_key: str | None) -> Project: ...
    async def get(self, project_id: uuid.UUID) -> Project: ...
    async def advance(self, project_id: uuid.UUID, dst: str) -> Project:  # calls assert_transition
        ...
    async def set_links(self, project_id, *, prd_url=None, arch_url=None, repo_url=None, jira_key=None) -> Project: ...
```

`advance` loads the project, calls `assert_transition(project.status, dst)`, updates status, commits.

**Tests (Postgres fixture):** `test_create_sets_initialized`, `test_advance_enforces_transition`, `test_set_links_persists`.
**Commit:** `feat(m1): ProjectService with guarded transitions`

---

## Task 3: ApprovalService + endpoints

**Files:** Create `app/orchestrator/approvals.py`, `app/api/approvals.py`, `app/schemas/approval.py`; Test `tests/test_approvals.py`

Interface:

```python
class ApprovalService:
    async def create(self, project_id, approval_type: str, payload: dict) -> HumanApprovalRequest: ...
    async def get_pending(self, project_id) -> list[HumanApprovalRequest]: ...
    async def approve(self, approval_id, feedback: str | None) -> HumanApprovalRequest: ...
    async def reject(self, approval_id, feedback: str) -> HumanApprovalRequest: ...   # feedback required
    async def wait_until_resolved(self, approval_id, *, poll_s: float = 2.0, timeout_s: float = 3600) -> HumanApprovalRequest: ...
```

`approval_type` ∈ `{PRD, ARCHITECTURE, EPICS, STORIES, ESCALATION}`. `wait_until_resolved` polls the row (MVP: simple DB poll; an agent coroutine awaits it before continuing). `reject` requires non-empty feedback (422 otherwise).

Endpoints:
- `GET /approvals/{project_id}/pending`
- `POST /approvals/{approval_id}/approve` body `{feedback?: str}`
- `POST /approvals/{approval_id}/reject` body `{feedback: str}`

**Tests:** `test_create_pending`, `test_approve_sets_resolved`, `test_reject_requires_feedback`, `test_endpoints_roundtrip` (TestClient).
**Commit:** `feat(m1): human approval service + endpoints`

---

## Task 4: Agent base (ReAct graph with scoped tools + logging)

**Files:** Create `app/agents/base.py`; Test `tests/test_agent_base.py`

Use LangGraph's prebuilt ReAct agent, bound to the agent's scoped tools and the logging callback:

```python
from langgraph.prebuilt import create_react_agent
from app.core.llm_client import get_llm
from app.mcp.client import MCPClientManager
from app.observability.callback import ToolLoggingCallbackHandler
from app.db.logs import record_agent_log

def build_agent(name: str, system_prompt: str, mcp: MCPClientManager, *, model: str | None = None,
                session_factory=None, **log_ids):
    tools = mcp.tools_for(name)
    llm = get_llm(model_override=model)

    async def record_fn(**kw):
        async with session_factory() as s:
            await record_agent_log(s, **kw); await s.commit()

    callback = ToolLoggingCallbackHandler(agent_name=name, record_fn=record_fn, **log_ids)
    graph = create_react_agent(llm, tools, state_modifier=system_prompt)
    return graph, callback  # caller invokes graph with config={"callbacks": [callback]}
```

**Test (mock mcp + llm):** `test_build_agent_binds_scoped_tools` asserts the graph's tools equal `tools_for(name)` and a callback is returned.
**Commit:** `feat(m1): agent base builder with scoped tools + logging`

---

## Task 5: PM Agent

**Files:** Create `app/agents/pm.py`, `app/schemas/agent_state.py`; Test `tests/test_pm_agent.py`

**Behavior:** conversational; maintains message history (persisted on the project via a `messages` JSON column or a side table — add `pm_messages JSONB` to `projects` in a small migration `0002`). Proactively asks about NFRs/compliance/scale. When the user confirms the draft, calls `confluence_create_page` to save the PRD, stores `confluence_prd_url`, then `ApprovalService.create(type="PRD", payload={prd_url, summary})`.

**State (TypedDict):**
```python
class PMState(TypedDict):
    project_id: str
    messages: list   # LangChain BaseMessage list
    prd_draft: str
    confluence_page_id: str | None
```

**System prompt:** adapt from `agents/product-manager.md` (PRD template + "always ask about NFRs/compliance/scale"). Tools available: PM scope from `tool_scopes.py`.

**Tests (mock Confluence tools):**
- `test_pm_asks_followup_when_nfrs_missing` (stub LLM returns a question; assert no Confluence write yet)
- `test_pm_saves_prd_and_requests_approval` (stub LLM emits the confirm + tool call; assert `confluence_create_page` called and a PRD approval row created)

**Commit:** `feat(m1): PM agent — idea to PRD with approval gate`

---

## Task 6: Architecture Agent (design + repo provisioning) — merges old Repo Bootstrap (D6)

**Files:** Create `app/agents/architecture.py`; Test `tests/test_architecture_agent.py`

**Graph:** `read_prd → propose_stack → await_stack_approval → write_arch_plan(Confluence) → create_repo → inject_files → request_final_approval`.

**Steps:**
1. `confluence_get_page` → approved PRD.
2. Propose tech stack + folder structure + DB schema → `ApprovalService.create(type="ARCHITECTURE", payload=...)`; wait.
3. On approval: `confluence_create_page` → architecture plan; store `confluence_arch_url`. `confluence_add_label("architecture")`.
4. `get_me` → owner; `create_repository`.
5. `push_files` to inject: `README.md` (links to Confluence), `docs/ARCHITECTURE.md` (the full plan), and the base skeleton from the spec (`app/main.py`, `requirements.txt`, `Dockerfile`, `.github/workflows/ci.yml`). Store `github_repo_url`.
6. `ProjectService.advance` → `ARCHITECTURE_APPROVED` then `REPO_BOOTSTRAPPING` → `PHASE_1_COMPLETE` is set after Jira too (dispatcher coordinates).

**Constraint:** the injected `docs/ARCHITECTURE.md` is the immutable reference Phase 2 agents read (Planning/Review).

**Tests (mock Confluence + GitHub tools):**
- `test_arch_requests_approval_before_repo` (no `create_repository` call before approval)
- `test_arch_creates_repo_and_injects_architecture_doc` (assert `create_repository` + `push_files` includes `docs/ARCHITECTURE.md` and `README.md`)

**Commit:** `feat(m1): architecture agent designs plan and provisions repo`

---

## Task 7: Jira Structuring Agent (Epic + Story sub-graphs)

**Files:** Create `app/agents/jira_structuring.py`; Test `tests/test_jira_structuring.py`

**Two-step graph with approval gates:**

*Epic Generator:* `confluence_get_page` (PRD) → group into 3–7 epics → `ApprovalService.create(type="EPICS", payload=epics)`; on approval `jira_create_issue(issueType="Epic")` per epic; store epic keys. Detect project via `jira_list_projects`/`jira_get_project`; validate fields with `jira_get_field_options`.

*Story Generator:* per approved epic → read `docs/ARCHITECTURE.md` (via `get_file_contents`) or arch Confluence page for technical notes → generate 3–6 stories (Given/When/Then) → `ApprovalService.create(type="STORIES", payload=stories)`; on approval `jira_create_issue(issueType="Story")` linked to epic. Per the **Jira MCP constraints**: create tech tasks as issue type **Task** (not Sub-task) and link to the Story via `jira_add_comment` listing related Task keys; document dependencies via comments (no `create_issue_link`).

**Tests (mock Jira tools):**
- `test_epics_require_approval_before_creation`
- `test_stories_created_as_tasks_and_linked_via_comment` (assert issue type `Task`, and a comment listing task keys is posted on the Story)

**Commit:** `feat(m1): jira structuring agent (epics→stories→tasks)`

---

## Task 8: Dispatcher + project/chat endpoints

**Files:** Create `app/orchestrator/dispatcher.py`, `app/api/projects.py`; Test `tests/test_dispatcher.py`

**Dispatcher** maps a project's state to the next action:

```python
PHASE1_ROUTES = {
    "PRD_APPROVED": "architecture",
    "ARCHITECTURE_APPROVED": ("architecture_repo", "jira_structuring"),  # repo + jira
    "EPICS_PENDING_APPROVAL": "jira_structuring_stories",
}
```

On approval resolution (called from the approve endpoint), the dispatcher advances state and triggers the next agent (background task). Endpoints:
- `POST /projects` → create project (INITIALIZED → PRD_DRAFTING), return id.
- `POST /projects/{id}/chat` → relay message to PM Agent, return assistant reply + whether a PRD approval is now pending.
- `GET /projects/{id}` → status + all links.
- `GET /projects/{id}/executions` → ticket executions (empty until Phase 2).

**Tests:** `test_dispatcher_routes_after_prd_approval`, `test_create_project_starts_drafting`, `test_chat_relays_to_pm` (mock PM graph).
**Commit:** `feat(m1): dispatcher + project/chat endpoints`

---

## Task 9: Phase 1 integration test (mocked MCP) + real-services verification gate

**Files:** Create `tests/integration/test_phase1_flow.py`

- [ ] **Integration test (mocked MCP tools, real Postgres):** drive the full flow programmatically — create project → chat until PRD saved → approve PRD → architecture proposes stack → approve → assert repo "created" (mock) + arch doc injected → epics generated → approve → stories generated → approve → project reaches `PHASE_1_COMPLETE`. Assert state transitions and that `agent_execution_logs` has rows per agent.

- [ ] **M1 VERIFICATION GATE — real services:** with real `MCP_SERVERS`, run an actual project:
  1. `POST /projects` then chat an idea → a **real Confluence PRD page** exists; approve it.
  2. Architecture proposes stack; approve → a **real Confluence architecture page** + a **real GitHub repo** with `docs/ARCHITECTURE.md` + README exist.
  3. Approve epics → **real Jira Epics**; approve stories → **real Jira Stories + Tasks**, tasks linked via comment.
  4. `GET /projects/{id}` shows all four links populated; project status `PHASE_1_COMPLETE`.

**Commit:** `test(m1): phase 1 integration flow + verification`

---

## Self-Review (M1)

- **Spec coverage:** FR-01..FR-07 (chat PRD, Confluence save, architecture plan, repo provision, epics, stories, approval gates) all map to Tasks 5–9. Repo Bootstrap folded into Task 6 (D6).
- **Approval gates:** PRD (Task 5), Architecture (Task 6), Epics + Stories (Task 7) — all via `ApprovalService`.
- **Jira constraints:** Task 7 explicitly uses Task-not-Subtask + comment linking.
- **Open item for execution:** confirm the target Jira project has the issue types and an "AI Ready" status (needed by M2); validate during the M1 gate.
- **Refine before build:** expand Tasks 5–7 (agent graphs) into bite-sized TDD steps via writing-plans, since their exact node functions depend on the LangGraph version pinned in M0.
