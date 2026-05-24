# AI Engineering Orchestrator (AEO)
### Human-in-the-Loop Autonomous SDLC Automation Platform
### Detailed Project Document — v1.0 | February 2026

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [System Philosophy](#3-system-philosophy)
4. [High-Level Architecture](#4-high-level-architecture)
5. [Phase 1 — Project Initialization](#5-phase-1--project-initialization)
   - 5.1 Product Manager Agent
   - 5.2 Architecture Agent
   - 5.3 Repo Bootstrap Agent
   - 5.4 Jira Structuring Agent
6. [Phase 2 — Recurrent Ticket Execution](#6-phase-2--recurrent-ticket-execution)
   - 6.1 Planning Agent
   - 6.2 Dev Agent
   - 6.3 QA Agent
   - 6.4 Review Agent
   - 6.5 Jira Update Agent
7. [Orchestrator Design](#7-orchestrator-design)
8. [State Machine](#8-state-machine)
9. [MCP Integration Layer](#9-mcp-integration-layer)
10. [Skill Design & Abstraction](#10-skill-design--abstraction)
11. [Data Models](#11-data-models)
12. [Technology Stack](#12-technology-stack)
13. [Human-in-the-Loop Governance](#13-human-in-the-loop-governance)
14. [Functional Requirements](#14-functional-requirements)
15. [Non-Functional Requirements](#15-non-functional-requirements)
16. [Success Metrics](#16-success-metrics)
17. [MVP Scope & Out of Scope](#17-mvp-scope--out-of-scope)
18. [Risks & Mitigations](#18-risks--mitigations)
19. [30-Day Build Breakdown](#19-30-day-build-breakdown)
20. [Future Enhancements](#20-future-enhancements)
21. [Strategic Positioning](#21-strategic-positioning)

---

## 1. Executive Summary

**AI Engineering Orchestrator (AEO)** is a human-supervised, multi-agent system that automates the full Software Development Life Cycle (SDLC) — from an idea discussed in a chat interface, all the way to tested, reviewed, and merged code in GitHub.

The system is built as an **AI Engineering OS** — an event-driven, stateful control plane that routes work to specialized AI agents, each with clearly scoped responsibilities. It integrates natively with the enterprise toolchain:

| Tool | Role |
|---|---|
| **Confluence** | PRD source of truth, Architecture memory |
| **Jira** | Ticket lifecycle, Epics, Stories |
| **GitHub** | Code repository, PRs, CI/CD |
| **Local Execution** | Test runner, Linter, Formatter |

AEO is **not a chatbot** and **not a code generator**. It is an organization of AI agents that mirrors how a structured engineering team operates — with human approval gates, tool governance, retry logic, and full traceability.

---

## 2. Problem Statement

Modern software engineering teams lose 30–40% of operational cycles to administrative and transitional tasks:

- Translating vague ideas into structured PRDs
- Manually breaking PRDs into Jira Epics and Stories
- Setting up boilerplate GitHub repositories
- Maintaining alignment between Jira tickets and GitHub code
- Writing repetitive unit tests
- Manually updating Jira ticket statuses after merges

**Current AI tools (GitHub Copilot, Cursor, etc.) solve micro-level code generation but fail to orchestrate the end-to-end SDLC.**

Key gaps:
- No unified architecture memory shared across tools
- No governance preventing agents from randomly breaking system boundaries
- No automated cross-system traceability (Jira ↔ GitHub)
- No self-correcting feedback loops tied to real CI results

**AEO solves this gap.**

---

## 3. System Philosophy

### Core Design Principles

| Principle | Description |
|---|---|
| **Human in the Loop** | Humans approve all major decisions (PRD, Architecture, Epics). Agents execute, humans govern. |
| **Agents Don't Own Tools** | Agents request skills. The Orchestrator executes via MCP. No agent directly calls an API. |
| **Architecture is Sacred** | Dev Agent cannot modify architecture, create new services, or change tech stack. Architecture Agent owns that boundary. |
| **State is Explicit** | Every project and ticket has tracked state. No implicit transitions. |
| **Failures are Recoverable** | Retry logic is capped, structured, and logged. No infinite loops. |
| **Traceability is Built-in** | Every action links Jira ↔ GitHub ↔ Confluence. |

### System Model

```
Idea → Chat Interface → PRD (Confluence) → Architecture Plan (Confluence)
     → GitHub Repo → Jira Epics/Stories
     → Per-Ticket: Plan → Code → QA → Review → Merge → Jira Done
```

---

## 4. High-Level Architecture

```
┌────────────────────────────────────────────────────────────┐
│                     CONTROL PLANE                          │
│                                                            │
│   ┌─────────────┐   ┌─────────────┐   ┌───────────────┐   │
│   │  Event      │   │  State      │   │   Agent       │   │
│   │  Listener   │──▶│  Machine    │──▶│   Dispatcher  │   │
│   │  (Webhooks) │   │  (Postgres) │   │               │   │
│   └─────────────┘   └─────────────┘   └───────┬───────┘   │
│                                               │           │
│                          ┌────────────────────┘           │
│                          ▼                                 │
│                  ┌───────────────┐                         │
│                  │ Skill Executor│                         │
│                  └───────┬───────┘                         │
└──────────────────────────┼─────────────────────────────────┘
                           │
         ┌─────────────────┼──────────────────┐
         ▼                 ▼                  ▼
  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐
  │ Confluence  │  │  Jira MCP    │  │   GitHub MCP     │
  │    MCP      │  │              │  │                  │
  └─────────────┘  └──────────────┘  └──────────────────┘
                                     ┌──────────────────┐
                                     │  Local Execution │
                                     │      MCP         │
                                     └──────────────────┘
```

### Architecture Layers

| Layer | Components | Purpose |
|---|---|---|
| **Control Plane** | FastAPI Orchestrator, State DB, Event Handler | Route work, track state, manage retries |
| **Agent Layer** | PM, Architecture, Repo, Jira, Planning, Dev, QA, Review, Release | Execute domain-specific tasks |
| **MCP Integration** | Confluence, Jira, GitHub, Local Execution MCPs | Abstracted tool execution |
| **Storage** | Postgres, Optional Vector DB, Log Storage (S3) | Persistence and memory |
| **Frontend** | Next.js Dashboard | Human approval interface |

---

## 5. Phase 1 — Project Initialization

Phase 1 is **collaborative and human-driven**. It runs once per project.

**Goal:** Idea → PRD → Architecture → Repo → Jira Board

---

### 5.1 Product Manager Agent

**Role:** Interactive chat interface that transforms raw ideas into structured PRDs.

**Type:** ReAct Agent with session memory and tool access.

#### Input Sources
- Direct brainstorming chat with user
- Uploaded documents (Word, PDF, Notion export)
- Existing Confluence pages
- User edits and corrections

#### Behavior
The PM Agent is conversational and iterative. It does **not** passively accept input — it actively asks questions to fill gaps:

```
Agent: "You mentioned a user authentication feature. Should this support 
        SSO/OAuth or email+password only?"

Agent: "What's your expected user base in Year 1? This will affect 
        infrastructure and scaling decisions."

Agent: "You haven't mentioned data retention requirements. Do you have 
        regulatory constraints (GDPR, HIPAA)?"
```

#### PRD Sections Extracted
| Section | Description |
|---|---|
| Problem Statement | What problem does this solve and for whom? |
| Target Users | Primary and secondary user personas |
| Core Features | Prioritized feature list (MVP vs. Phase 2) |
| Non-Functional Requirements | Performance, security, scalability, compliance |
| Constraints | Tech, time, team, budget limitations |
| KPIs & Success Metrics | Measurable outcomes |
| Out of Scope | Explicit exclusions to prevent scope creep |

#### Tools (via MCP)
```
Confluence MCP:
- create_page        → Creates the PRD page
- update_page        → Iterative refinement
- fetch_page         → Read existing PRD drafts
- search_pages       → Reference related pages

Memory:
- session_memory     → Remembers context within conversation
- prd_draft_memory   → Stores working draft state
```

#### Output
A **fully structured PRD page in Confluence** — this becomes **Project Source of Truth #1**.

Human explicitly approves before Phase 1 continues.

---

### 5.2 Architecture Agent

**Role:** Deep technical translator that converts the approved PRD into a concrete architecture plan.

**Type:** ReAct Agent with human-in-loop approval step and web research capability.

**Trigger:** Human approval of PRD.

#### Responsibilities

The Architecture Agent reads the PRD and proposes the following, asking human for confirmation at each major decision:

**A. Tech Stack Selection**
```
Backend:     Python / FastAPI (or Node.js/Express)
Database:    PostgreSQL / MongoDB (based on data model)
Auth:        JWT / OAuth2
Queue:       Redis / Celery (if async processing needed)
Deployment:  Docker + GitHub Actions
Cloud:       AWS (EC2/RDS) or GCP (Cloud Run/Cloud SQL)
```

**B. Folder Structure**
```
project-name/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── routes/
│   │       └── dependencies/
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── main.py
├── tests/
│   ├── unit/
│   └── integration/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .github/
│   └── workflows/
│       └── ci.yml
└── README.md
```

**C. Database Schema Outline**
- Entity relationships
- Primary tables and key fields
- Indexing strategy
- Migration approach (Alembic)

**D. Testing Strategy**
```
Unit Tests:        pytest + pytest-mock
Integration Tests: pytest + TestClient (FastAPI)
Coverage Target:   ≥ 80%
CI Gate:           Tests must pass before merge
```

**E. CI/CD Plan**
```
GitHub Actions pipeline:
1. Install dependencies
2. Run linter (flake8/ruff)
3. Run formatter check (black)
4. Run pytest
5. Generate coverage report
6. (Optional) Build Docker image
```

**F. Deployment Target**
- Container: Docker
- Orchestration: Docker Compose (local) / ECS or Cloud Run (cloud)
- Environment management: .env files + secrets manager

#### Human-in-Loop Checkpoints
1. Agent proposes tech stack → Human approves or modifies
2. Agent proposes folder layout → Human confirms
3. Agent proposes DB schema → Human reviews
4. Final architecture summary → Human approves before Repo Bootstrap begins

#### Tools (via MCP)
```
Confluence MCP:
- fetch_page          → Read approved PRD
- create_page         → Create Architecture Plan page
- update_page         → Refine based on human feedback

Optional:
- web_search          → Research best practices, compare frameworks

Memory:
- architecture_memory → Persisted; used by all Phase 2 agents
```

#### Output
**Architecture Plan page in Confluence** containing tech stack, folder structure, DB schema, CI strategy, testing approach, and deployment plan — this becomes **Project Source of Truth #2**.

---

### 5.3 Repo Bootstrap Agent

**Role:** Provisions the GitHub repository with the base project skeleton.

**Type:** Deterministic agent (no LLM reasoning needed for most steps) — follows the approved architecture plan.

**Trigger:** Human approval of Architecture Plan.

#### Responsibilities

| Step | Action |
|---|---|
| 1 | Create GitHub repository (public or private) |
| 2 | Generate folder structure per architecture plan |
| 3 | Create base FastAPI `main.py` |
| 4 | Write `requirements.txt` |
| 5 | Write `Dockerfile` |
| 6 | Write `docker-compose.yml` |
| 7 | Write `.github/workflows/ci.yml` (GitHub Actions) |
| 8 | Write `README.md` with project overview |
| 9 | Commit all files as initial commit |
| 10 | Create "Project Setup" issue in GitHub for visibility |

#### Generated Files (Examples)

**`main.py` (Base FastAPI App)**
```python
from fastapi import FastAPI
from app.api.v1 import router
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME, version="0.1.0")
app.include_router(router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "ok"}
```

**`ci.yml` (GitHub Actions)**
```yaml
name: CI Pipeline
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - run: ruff check .
      - run: pytest tests/ --cov=app --cov-report=term
```

#### Tools (via MCP)
```
GitHub MCP:
- create_repo      → Create the GitHub repository
- create_branch    → Set up main branch
- commit_files     → Push all template files
- create_issue     → Open "Project Setup" tracking issue
```

#### Output
**Live GitHub repository** with base skeleton — this becomes the **Code Source of Truth**.

---

### 5.4 Jira Structuring Agent

**Role:** Converts the approved PRD into a structured Jira board with Epics and Stories.

**Type:** Two-step multi-agent process with human review gates.

**Trigger:** GitHub repo confirmed live.

---

#### Step A — PRD to Epics (Epic Generator Sub-Agent)

**Process:**
1. Fetch PRD from Confluence
2. Identify major functional areas (e.g., "User Authentication", "Dashboard", "API Integration")
3. Create one Epic per functional area
4. Write a clear Epic description and business goal

**Output per Epic:**
```
Epic: User Authentication
Goal: Allow users to register, login, and manage sessions securely
Priority: High
Estimated Stories: 4-6
```

Human reviews and approves all Epics before Story generation begins.

---

#### Step B — Epics to Stories (Story Generator Sub-Agent)

**Process:** Iterates over each approved Epic and generates Stories.

**Per Story includes:**
```
Title:               As a [user], I want to [action] so that [benefit]
Acceptance Criteria: Given/When/Then format
Technical Notes:     Files to modify, DB changes, dependencies
Complexity:          S / M / L (optional, for sprint planning)
Labels:              backend / frontend / infra / docs
```

**Example:**
```
Story: Implement user registration endpoint
Label: backend

Acceptance Criteria:
  - Given valid email and password, POST /auth/register returns 201
  - Given duplicate email, returns 409 Conflict
  - Password must be hashed (bcrypt)
  - Returns JWT access token on success

Technical Notes:
  - Modify: app/api/v1/routes/auth.py
  - DB: Add users table (id, email, hashed_password, created_at)
  - Use: passlib for hashing, python-jose for JWT
```

Human can modify any Story before it is created in Jira.

#### Tools (via MCP)
```
Jira MCP:
- create_epic          → Create each epic
- create_story         → Create each story
- link_story_to_epic   → Establish parent-child relationship
- update_issue         → Apply labels, descriptions, acceptance criteria
```

#### Output
**Fully structured Jira board** with all Epics and Stories linked. Team can now start Phase 2.

---

## 6. Phase 2 — Recurrent Ticket Execution

Phase 2 is **event-driven and semi-autonomous**. It runs for every Jira ticket.

**Trigger:** Jira ticket moves to status **"AI Ready"**

**Goal:** Jira Story → Planned → Coded → Tested → Reviewed → Merged → Jira Done

---

### 6.1 Planning Agent

**Role:** Analyzes the Jira story and creates a structured implementation plan as a GitHub Issue.

**Does NOT write code.** Defines the execution blueprint.

#### Responsibilities

| Step | Action |
|---|---|
| 1 | Fetch Jira ticket (story, acceptance criteria, labels) |
| 2 | Fetch Architecture Plan from Confluence |
| 3 | Analyze current repo file tree |
| 4 | Identify exact files to create or modify |
| 5 | Identify DB changes required |
| 6 | Identify test files to create |
| 7 | Create a structured GitHub Issue |
| 8 | Assign issue to "AI Dev" (Dev Agent trigger) |

#### GitHub Issue Format (Output)
```markdown
## Implementation Plan: [Jira Story Title]

**Jira Ticket:** [PROJ-42]
**Epic:** [PROJ-10 - User Authentication]

### Files to Modify
- `app/api/v1/routes/auth.py` — Add POST /auth/register endpoint
- `app/models/user.py` — Create User SQLAlchemy model
- `app/schemas/user.py` — Create UserCreate, UserResponse schemas
- `app/services/auth_service.py` — Business logic for registration

### Database Changes
- Create table: `users` (id UUID PK, email VARCHAR UNIQUE, hashed_password VARCHAR, created_at TIMESTAMP)
- Run: Alembic migration

### Tests Required
- `tests/unit/test_auth_service.py` — Unit test register logic
- `tests/integration/test_auth_routes.py` — Integration test endpoints

### Acceptance Criteria (from Jira)
- POST /auth/register returns 201 on success
- Returns 409 on duplicate email
- Password is bcrypt-hashed
```

#### Tools (via MCP)
```
Jira MCP:        fetch_issue
Confluence MCP:  fetch_page (architecture memory)
GitHub MCP:      create_issue, read_file_tree
```

---

### 6.2 Dev Agent

**Role:** Implements the feature based on the Planning Agent's GitHub Issue.

**Trigger:** GitHub Issue created and assigned by Planning Agent.

#### Responsibilities

| Step | Action |
|---|---|
| 1 | Read GitHub Issue (implementation plan) |
| 2 | Read relevant existing files from repo |
| 3 | Read Architecture Memory (constraints) |
| 4 | Create feature branch: `feature/PROJ-42-user-registration` |
| 5 | Write/modify all files per the plan |
| 6 | Commit with structured message |
| 7 | Open Pull Request linked to Jira ticket |

#### Constraints (STRICTLY ENFORCED by Orchestrator)
- Must not add new services beyond architecture plan
- Must not change tech stack
- Must not modify database structure beyond what Planning Agent specified
- Must follow existing folder/naming conventions
- PR description must reference Jira ticket number

#### Commit Message Format
```
feat(PROJ-42): Add user registration endpoint

- Add POST /auth/register with bcrypt password hashing
- Create User model and Alembic migration
- Add UserCreate/UserResponse Pydantic schemas
- Add auth_service with register business logic

Refs: PROJ-42
```

#### Tools (via MCP)
```
GitHub MCP:
- create_branch    → Create feature branch
- read_file        → Read existing code
- commit_files     → Push code changes
- open_pr          → Open pull request

Local Execution MCP:
- format_code      → Run black formatter before commit
- lint             → Run ruff/flake8 before commit
```

---

### 6.3 QA Agent

**Role:** Validates the Dev Agent's implementation through automated testing.

**Trigger:** Pull Request opened by Dev Agent.

#### Responsibilities

| Step | Action |
|---|---|
| 1 | Read the PR diff |
| 2 | Read the Planning Agent's test requirements |
| 3 | Generate unit and integration tests |
| 4 | Run pytest locally |
| 5 | Parse test results |
| 6 | Post results as PR comment |

#### On Test Failure
```
1. Parse structured failure logs
2. Create structured bug report:
   {
     "failing_test": "test_register_duplicate_email",
     "error_type": "AssertionError",
     "expected": "409",
     "got": "500",
     "line": "auth_routes.py:48",
     "root_cause_hypothesis": "Missing duplicate email handling in service layer"
   }
3. Send to Dev Agent for fix
4. Increment retry counter
```

**Max Retries: 3**
After 3 failures, escalate to human reviewer with full failure log.

#### Tools (via MCP)
```
Local Execution MCP:
- run_tests        → Execute pytest
- parse_logs       → Structured failure parsing
- run_linter       → Code quality check

GitHub MCP:
- comment_on_pr    → Post test results
- read_pr_diff     → Analyze changes
```

---

### 6.4 Review Agent

**Role:** Final quality gate. Evaluates the PR against Jira acceptance criteria and architecture constraints.

**Trigger:** QA Agent marks tests as passed.

#### Review Checklist

| Category | Checks |
|---|---|
| **Acceptance Criteria** | Does code satisfy all Given/When/Then criteria from Jira? |
| **Architecture Compliance** | Does this follow the approved architecture plan? No boundary violations? |
| **Code Quality** | No obvious anti-patterns, dead code, or hardcoded secrets? |
| **Test Coverage** | Are all critical paths tested? |
| **Security** | No SQL injection risk, secrets in code, or insecure defaults? |
| **PR Description** | References Jira ticket, describes changes clearly? |

#### Decision Logic
```
IF all checks pass:
  → Approve PR
  → Trigger merge
  → Trigger Jira Update Agent

IF issues found:
  → Post structured review comments on PR
  → Label PR: "changes-requested"
  → Send structured feedback to Dev Agent for revision
```

#### Review Comment Format
```markdown
## Review Agent Feedback

**Status:** Changes Requested

### Issues Found:

1. [SECURITY] `auth_routes.py:32` — Password logged in plaintext. 
   Remove logging statement before merge.

2. [ARCHITECTURE] `auth_service.py:18` — Direct DB call in route handler.
   Per architecture plan, all DB operations must go through the service layer.

3. [TEST] Missing test for expired token scenario per acceptance criteria item 4.

**Action Required:** Dev Agent should address all 3 issues then re-request review.
```

---

### 6.5 Jira Update Agent

**Role:** Closes the feedback loop by updating Jira after successful merge.

**Trigger:** PR merged by Review Agent.

#### Responsibilities

| Step | Action |
|---|---|
| 1 | Move Jira ticket status → **Done** |
| 2 | Add PR link to Jira ticket |
| 3 | Add summary comment to Jira ticket |

#### Jira Comment Format
```
✅ AEO — Automated Update

PR Merged: https://github.com/org/repo/pull/47
Branch: feature/PROJ-42-user-registration
Merged by: Review Agent (AEO)

Summary:
- Implemented POST /auth/register endpoint
- Added User model and migration
- 8 unit tests, 4 integration tests — all passing
- CI pipeline: ✅ Passed

Cycle Time: 47 minutes from AI Ready → Merged
```

---

## 7. Orchestrator Design

The Orchestrator is the **central nervous system** of AEO. It is built on FastAPI and acts as:

- **Event Listener** — Receives webhooks from Jira and GitHub
- **State Manager** — Tracks project and ticket state in Postgres
- **Agent Dispatcher** — Selects and activates the correct agent
- **Skill Executor** — Routes agent skill requests to correct MCP server
- **Retry Controller** — Enforces retry caps and failure escalation

### Orchestrator Responsibilities

| Responsibility | Detail |
|---|---|
| **Workflow Management** | Maintains project state, ticket state, retry counters, failure paths |
| **Agent Routing** | Selects agent, passes structured state, receives and validates output schema |
| **Skill Invocation** | Agents request skills → Orchestrator executes via MCP (agents never call APIs directly) |
| **Event Handling** | Responds to: New PRD, Jira ticket created, PR opened, CI failed, CI passed, PR merged |

### Event → Agent Routing Table

| Trigger Event | Agent Activated |
|---|---|
| User starts chat session | PM Agent |
| PRD approved by human | Architecture Agent |
| Architecture approved | Repo Bootstrap Agent + Jira Structuring Agent (parallel) |
| Epics approved | Story Generator Sub-Agent |
| Jira ticket → AI Ready | Planning Agent |
| GitHub Issue created | Dev Agent |
| PR opened | QA Agent |
| Tests passed | Review Agent |
| PR approved | Merge + Jira Update Agent |
| Tests failed (retry < 3) | Dev Agent (fix mode) |
| Tests failed (retry = 3) | Human escalation |

### Skill-Based Agent Activation

Ticket labels drive additional routing logic:

```
label = "backend"  → Activate Dev Agent + QA Agent
label = "docs"     → Skip QA test generation
label = "infra"    → Activate DevOps Agent (Phase 2+)
label = "hotfix"   → Skip Epic grouping, direct to Dev Agent
```

---

## 8. State Machine

### Ticket State Machine

Every Jira ticket tracked by AEO follows this state machine:

```
AI_READY
   │
   ▼
PLANNING
   │
   ▼
IN_DEVELOPMENT
   │
   ▼
IN_QA
   │
   ├──[tests failed, retry < 3]──▶ FIXING ──▶ IN_QA
   │
   ├──[tests failed, retry = 3]──▶ ESCALATED (human)
   │
   ▼
READY_TO_MERGE
   │
   ▼ [Review Agent: approved]
MERGED
   │
   ▼
JIRA_UPDATED (Done)
```

**State Transition Rules:**
- Transitions are only triggered by explicit agent output validation
- Each transition is logged with timestamp, agent name, and result
- `FIXING` state has a hard ceiling of 3 transitions
- `ESCALATED` requires human intervention to re-enter the machine

### Project State Machine (Phase 1)

```
INITIALIZED
   │
   ▼
PRD_DRAFTING
   │
   ▼ [human approves PRD]
PRD_APPROVED
   │
   ▼
ARCHITECTURE_DESIGN
   │
   ▼ [human approves architecture]
ARCHITECTURE_APPROVED
   │
   ├──▶ REPO_BOOTSTRAPPING
   └──▶ JIRA_STRUCTURING (parallel)
         │
         ▼
      EPICS_PENDING_APPROVAL
         │
         ▼ [human approves epics]
      STORIES_GENERATING
         │
         ▼ [human approves stories]
PHASE_1_COMPLETE → Phase 2 begins
```

---

## 9. MCP Integration Layer

All external tool interactions are abstracted through **Model Context Protocol (MCP) Servers**. Agents **never call APIs directly**.

### MCP Server 1 — Confluence MCP

**Purpose:** All Confluence read/write operations

| Skill | Description |
|---|---|
| `fetch_page` | Read a Confluence page by ID or title |
| `create_page` | Create a new page in a specified space |
| `update_page` | Update existing page content |
| `search_pages` | Full-text search across Confluence space |

---

### MCP Server 2 — Jira MCP

**Purpose:** All Jira read/write operations

| Skill | Description |
|---|---|
| `fetch_issue` | Get full issue details by key |
| `create_epic` | Create an Epic with description |
| `create_story` | Create a Story linked to an Epic |
| `link_story_to_epic` | Set parent-child relationship |
| `update_ticket_status` | Transition ticket (e.g., AI Ready → In Dev → Done) |
| `add_ticket_comment` | Add structured comment to ticket |
| `update_issue` | Update fields, labels, priority |

---

### MCP Server 3 — GitHub MCP

**Purpose:** All GitHub repository operations

| Skill | Description |
|---|---|
| `create_repo` | Initialize a new GitHub repository |
| `create_branch` | Create feature branch from main |
| `read_file` | Read file contents from repo |
| `read_file_tree` | Get repository folder structure |
| `commit_files` | Push one or more file changes |
| `open_pr` | Open a Pull Request with description |
| `comment_on_pr` | Add comment (QA results, review feedback) |
| `get_pr_diff` | Get structured PR diff |
| `get_ci_status` | Check GitHub Actions status |
| `merge_pr` | Merge approved PR |
| `create_issue` | Create GitHub issue |

---

### MCP Server 4 — Local Execution MCP (Critical for QA)

**Purpose:** Run code locally in a sandboxed environment

| Skill | Description |
|---|---|
| `run_tests` | Execute pytest and return structured results |
| `run_linter` | Run ruff/flake8 and return violations |
| `format_code` | Run black formatter |
| `parse_logs` | Convert raw test output to structured JSON |
| `read_coverage_report` | Extract coverage % per module |

---

### MCP Server 5 — Cloud Deployment MCP (Phase 2+, Optional)

**Purpose:** Container deployment and management

| Skill | Description |
|---|---|
| `deploy_container` | Deploy Docker container to cloud |
| `get_deployment_status` | Check if deployment is healthy |
| `rollback_deployment` | Roll back to previous version |

---

## 10. Skill Design & Abstraction

### How Skills Work

Agents do NOT know how to call APIs. They request skills as structured JSON:

```json
{
  "skill": "create_github_branch",
  "input": {
    "repo": "org/project-name",
    "branch_name": "feature/PROJ-42-user-registration",
    "base_branch": "main"
  }
}
```

The Orchestrator:
1. Receives the skill request
2. Validates the input schema
3. Routes to the correct MCP server
4. Executes the action
5. Returns structured result

```json
{
  "skill": "create_github_branch",
  "status": "success",
  "output": {
    "branch_url": "https://github.com/org/repo/tree/feature/PROJ-42",
    "sha": "abc123"
  }
}
```

### Skill Categories Summary

| Category | Skills |
|---|---|
| **Repo Skills** | `create_repo`, `create_branch`, `commit_files`, `open_pr`, `merge_pr`, `get_ci_status` |
| **Jira Skills** | `create_epic`, `create_story`, `update_ticket_status`, `add_ticket_comment` |
| **Confluence Skills** | `fetch_page`, `create_page`, `update_page`, `search_pages` |
| **Testing Skills** | `run_tests`, `run_linter`, `parse_test_logs`, `read_coverage_report` |
| **Planning Skills** | `retrieve_architecture_memory`, `retrieve_repo_structure`, `search_codebase` |
| **Governance Skills** | `record_execution_log`, `calculate_token_usage`, `record_retry_event` |

---

## 11. Data Models

### Project Record

```sql
CREATE TABLE projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    status          VARCHAR(50) NOT NULL,  -- INITIALIZED, PRD_APPROVED, PHASE_1_COMPLETE, etc.
    confluence_prd_url     TEXT,
    confluence_arch_url    TEXT,
    github_repo_url        TEXT,
    jira_project_key       VARCHAR(50),
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);
```

### Ticket Execution Record

```sql
CREATE TABLE ticket_executions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID REFERENCES projects(id),
    jira_ticket_key VARCHAR(50) NOT NULL,
    github_issue_url       TEXT,
    github_pr_url          TEXT,
    status          VARCHAR(50) NOT NULL,  -- AI_READY, PLANNING, IN_DEVELOPMENT, IN_QA, etc.
    retry_count     INTEGER DEFAULT 0,
    current_agent   VARCHAR(100),
    last_error      TEXT,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);
```

### Agent Execution Log

```sql
CREATE TABLE agent_execution_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_execution_id UUID REFERENCES ticket_executions(id),
    agent_name      VARCHAR(100) NOT NULL,
    skill_requested VARCHAR(100),
    input_payload   JSONB,
    output_payload  JSONB,
    status          VARCHAR(50),  -- success, failed, retrying
    token_usage     INTEGER,
    duration_ms     INTEGER,
    created_at      TIMESTAMP DEFAULT NOW()
);
```

---

## 12. Technology Stack

| Layer | Technology | Justification |
|---|---|---|
| **Frontend** | Next.js (TypeScript) | Interactive chat UI, dashboard, human approval flows |
| **Backend Orchestrator** | FastAPI (Python) | Async-first, webhook handling, fast API layer |
| **LLM Framework** | LangChain / LangGraph | Agent reasoning, memory, tool routing, state graphs |
| **LLM Provider** | OpenAI GPT-4o / Anthropic Claude 3.5 | Reasoning quality for agent tasks |
| **State Database** | Supabase (PostgreSQL) | Relational state tracking, free tier, row-level security |
| **Vector Memory** | Chroma / Supabase pgvector | Architecture memory retrieval (optional MVP) |
| **MCP Servers** | Python-based MCP servers | Abstracted tool execution |
| **Code Execution** | Docker sandbox / subprocess | Safe local test execution |
| **CI/CD** | GitHub Actions | Triggered by PR events, linting, testing |
| **Log Storage** | S3 / Supabase Storage | Agent execution logs, test output archives |

---

## 13. Human-in-the-Loop Governance

AEO is **not fully autonomous**. Human approval is required at these gates:

| Checkpoint | What Human Reviews | Consequence of Rejection |
|---|---|---|
| **PRD Approval** | Full structured PRD with all sections | PM Agent reopens, refines based on feedback |
| **Architecture Approval** | Tech stack, folder layout, DB schema, CI plan | Architecture Agent revises proposal |
| **Epic Approval** | List of all epics with descriptions | Epic Generator revises, removes, or adds epics |
| **Stories Approval** | All stories per epic with acceptance criteria | Story Generator revises individual stories |
| **Manual Escalation** | QA failures after 3 retries | Human debugs or modifies implementation plan |

### Human Interface (Next.js Dashboard)

The dashboard provides:
- **Chat Interface** — For PM Agent and Architecture Agent conversations
- **Approval Views** — Structured views for approving PRDs, Architectures, Epics, Stories
- **Execution Monitor** — Live view of ticket state, current agent, retry count
- **Logs Viewer** — Full agent execution history per ticket

---

## 14. Functional Requirements

| ID | Requirement |
|---|---|
| FR-01 | System must provide an interactive chat interface for PRD creation |
| FR-02 | System must save approved PRDs to Confluence |
| FR-03 | System must generate a complete architecture plan and save to Confluence |
| FR-04 | System must provision a GitHub repository from the architecture plan |
| FR-05 | System must generate Epics from PRD and create them in Jira |
| FR-06 | System must generate Stories from Epics and create them in Jira |
| FR-07 | System must support human approval before advancing each Phase 1 step |
| FR-08 | System must trigger Phase 2 when a Jira ticket enters "AI Ready" status |
| FR-09 | System must create a structured GitHub Issue before code generation |
| FR-10 | System must create a feature branch and implement code per the plan |
| FR-11 | System must open a Pull Request after code implementation |
| FR-12 | System must run automated tests and parse results |
| FR-13 | System must retry failed implementations up to 3 times |
| FR-14 | System must escalate to human after exceeding retry limit |
| FR-15 | System must enforce architecture constraints on all Dev Agent output |
| FR-16 | System must review PRs against Jira acceptance criteria |
| FR-17 | System must merge approved PRs automatically |
| FR-18 | System must update Jira ticket to Done after merge |
| FR-19 | System must add PR link and summary to Jira ticket |
| FR-20 | System must log all agent executions, token usage, and retries |

---

## 15. Non-Functional Requirements

### Performance
- Phase 1 (full initialization) should complete in < 30 minutes with human delays excluded
- Phase 2 (single ticket, happy path) should complete in < 20 minutes
- Webhook processing latency < 5 seconds

### Scalability
- Support up to 10 concurrent ticket executions (MVP)
- State database must be queryable without full table scans (proper indexing)

### Observability
All the following must be logged per execution:
- Agent name and version
- Skill requested
- Input/output payloads
- Token usage
- Duration
- Retry count
- Final status

### Reliability
- Retry capped at 3 per ticket
- Graceful degradation: if an MCP server is unavailable, ticket moves to ESCALATED (not silent failure)
- All state transitions are atomic

### Security
- All API keys stored as environment variables / secrets (never in code)
- GitHub tokens scoped to minimum required permissions
- Jira/Confluence tokens stored in .env (never committed)
- No secrets logged in execution logs

### Maintainability
- Each agent is independently defined and replaceable
- MCP servers are stateless and independently deployable
- Skills are documented with input/output schemas

---

## 16. Success Metrics

| Metric | Target |
|---|---|
| % tickets implemented without human coding | ≥ 70% (MVP) |
| Average retries per ticket | ≤ 1.2 |
| CI pass rate on first Dev Agent attempt | ≥ 60% |
| Time from "AI Ready" → Merged (happy path) | < 20 minutes |
| Phase 1 completion time (human delays excluded) | < 30 minutes |
| Jira ↔ GitHub traceability completeness | 100% of merged tickets |
| Escalation rate (retry cap hit) | < 15% of tickets |

---

## 17. MVP Scope & Out of Scope

### In Scope (MVP)

- PM Agent with chat interface
- Architecture Agent with human approval
- Repo Bootstrap Agent (FastAPI + GitHub)
- Jira Structuring Agent (Epics + Stories)
- Planning Agent (GitHub Issue generation)
- Dev Agent (branch, code, PR)
- QA Agent (pytest, retry loop)
- Review Agent (acceptance criteria check)
- Jira Update Agent (close ticket, add comment)
- Confluence MCP, Jira MCP, GitHub MCP, Local Execution MCP
- Postgres state machine
- Next.js human approval dashboard

### Out of Scope (MVP)

| Feature | Phase |
|---|---|
| Frontend/UI code generation | Phase 2+ |
| Multi-repo microservices | Phase 2+ |
| Automated cloud deployment | Phase 2+ |
| Real-time Slack/Teams notifications | Phase 2+ |
| Full SOC2 compliance tooling | Phase 3 |
| DevOps Agent (K8s, ECS) | Phase 2+ |
| Cost monitoring dashboard | Phase 2+ |
| Security scanning agent (SAST) | Phase 2+ |

---

## 18. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LLM hallucination in code generation | Medium | High | Architecture constraint enforcement; Planning Agent validates before Dev; schema validation on all outputs |
| Infinite retry loops | Low | High | Hard cap of 3 retries; escalation to human after cap |
| Dev Agent breaks repo structure | Medium | High | Orchestrator validates all file paths against architecture plan before commit |
| MCP server downtime | Low | Medium | Graceful failure with ticket moved to ESCALATED; retry after timeout |
| Jira/GitHub API rate limits | Low | Medium | Implement exponential backoff in MCP servers |
| Context window overflow for large PRDs | Medium | Medium | Chunked retrieval; summarization skill for large documents |
| Security: leaked API keys | Low | Critical | All keys in env variables; secret scanning on GitHub; never log credentials |

---

## 19. 30-Day Build Breakdown

### Week 1 — Foundation
- [ ] Set up FastAPI project structure
- [ ] Configure Supabase schema (projects, ticket_executions, agent_logs)
- [ ] Build Confluence MCP server (fetch_page, create_page, update_page)
- [ ] Build Jira MCP server (create_epic, create_story, update_status, fetch_issue)
- [ ] Build GitHub MCP server (create_repo, create_branch, commit_files, open_pr)

### Week 2 — Phase 1 Agents
- [ ] Build PM Agent (ReAct, session memory, Confluence tools)
- [ ] Build Architecture Agent (structured output, human approval loop)
- [ ] Build Repo Bootstrap Agent (deterministic, file generation)
- [ ] Build Jira Structuring Agent (Epic sub-agent + Story sub-agent)
- [ ] Wire Phase 1 state machine in Orchestrator

### Week 3 — Phase 2 Agents
- [ ] Build Planning Agent (repo analysis, GitHub Issue generation)
- [ ] Build Dev Agent (branch, code generation, PR)
- [ ] Build Local Execution MCP server (pytest, ruff, black, log parsing)
- [ ] Build QA Agent (test generation, run pytest, retry logic)
- [ ] Build Review Agent (acceptance criteria comparison, feedback)
- [ ] Build Jira Update Agent (status update, comment)
- [ ] Wire Phase 2 state machine and retry logic

### Week 4 — Frontend + Integration
- [ ] Build Next.js dashboard with chat interface
- [ ] Build approval views (PRD, Architecture, Epics, Stories)
- [ ] Build execution monitor (ticket state, current agent, logs)
- [ ] End-to-end integration test: idea → merged PR → Jira Done
- [ ] Observability: log viewer, token usage tracking
- [ ] Final bug fixes and documentation

---

## 20. Future Enhancements

| Enhancement | Description |
|---|---|
| **DevOps Agent** | Automate deployment to AWS ECS or GCP Cloud Run after merge |
| **Security Scanning Agent** | Run Bandit/Semgrep on PR before review; block on critical issues |
| **Cost Monitoring** | Track LLM token usage per ticket; estimate project cost |
| **Slack Integration** | Notify team on human approval needed, escalations, and merges |
| **Multi-Agent Collaboration** | Planning Agent and Dev Agent can discuss plan before execution |
| **Skill-Based Dynamic Routing** | More granular routing based on ticket labels and complexity |
| **Frontend Code Generation** | Extend Dev Agent to generate React/Next.js components |
| **Multi-Repo Support** | Handle microservices projects with multiple repositories |
| **Vector Memory Upgrade** | Semantic search over codebase and architecture history |
| **Evaluation Dashboard** | Measure agent performance, accuracy, and improvement over time |

---

## 21. Strategic Positioning

### What AEO Is

> A **Human-Supervised AI-Native Engineering Organization** operating across Confluence, Jira, and GitHub with structured governance, event-driven orchestration, and full tool abstraction.

### What AEO Is NOT
- A chatbot
- A code generator
- A CI/CD tool
- A Copilot replacement

### Engineering Concepts Demonstrated

| Concept | How AEO Demonstrates It |
|---|---|
| Event-Driven Architecture | Jira/GitHub webhooks trigger state transitions |
| State Machine Design | Explicit ticket lifecycle with guarded transitions |
| Multi-Agent Orchestration | 9+ specialized agents with scoped responsibilities |
| Tool Abstraction Layer | Skill-based MCP model prevents API chaos |
| Human-in-Loop Governance | Approval gates at every high-stakes decision |
| Self-Correcting Feedback Loops | QA → Dev retry cycle with structured error propagation |
| Enterprise Tool Integration | Confluene + Jira + GitHub as first-class citizens |
| Observability | Full execution logging, token tracking, retry counting |
| Fault Tolerance | Retry caps, graceful degradation, escalation paths |

---

*Document Version: 1.0*
*Created: February 2026*
*Project: AI Engineering Orchestrator (AEO)*
*Status: Active — Pre-Build Phase*
