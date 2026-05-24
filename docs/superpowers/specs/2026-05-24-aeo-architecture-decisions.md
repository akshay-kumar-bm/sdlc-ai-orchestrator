# AEO — Architecture Decisions (Pre-Build)

> **Status:** Approved 2026-05-24. Refines `IMPLEMENTATION_SPEC.md` (v1.1) and `project_detail.md` (v1.0). Where this document and the older spec disagree, **this document wins**.

This records the decisions made during the brainstorming pass on 2026-05-24, before writing the milestone implementation plans. The high-level design lives in `project_detail.md`; the build-level spec in `IMPLEMENTATION_SPEC.md`. This doc captures only the *deltas* and the locked execution plan.

---

## 1. Locked Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | **Use the existing MCP servers** (Confluence, Jira, GitHub) — connect to them as a client. Do **not** build or run custom integration servers/clients. | The backend is the sole consumer; the user's environment already has these MCP servers configured. Building our own is redundant. |
| D2 | **Local execution is the only integration we own** — clone + `pytest` + `ruff` via subprocess, in-process, no server. | No off-the-shelf MCP server runs project tests in a sandbox. |
| D3 | **Drop the central `SkillExecutor` / skill registry.** Govern by binding a **scoped subset of MCP tools per agent** (LangGraph native tool calling). | The indirection only added value for many external clients. With one in-process consumer, per-agent tool scoping achieves the same governance with far less code. |
| D4 | **Observability via a LangGraph callback** that logs every tool call to `agent_execution_logs` (agent, tool, input, output, tokens, duration, status). | Keeps the spec's observability requirement without the SkillExecutor. |
| D5 | **Architecture-constraint enforcement moves to the Review Agent** (post-hoc check), not pre-commit interception. | Copilot writes code autonomously; we cannot intercept its file writes. The Review Agent verifies compliance against the architecture plan before merge. |
| D6 | **Merge Architecture Agent + Repo Bootstrap Agent** into one **Architecture Agent** that designs the system, writes the Confluence plan, creates the repo, and injects `docs/ARCHITECTURE.md` + README + skeleton. | Matches the existing `agents/solution-architecture.md`, which already does both. Reduces 9 agents → 7. |
| D7 | **Phase 2 is built around GitHub Copilot's coding agent.** Planning Agent creates a rich issue and calls `assign_copilot_to_issue`; Copilot autonomously branches, codes, runs tests, and opens a PR; it iterates from PR comments. | Confirmed available in the user's environment (GitHub MCP exposes `assign_copilot_to_issue`, `create_pull_request_with_copilot`, `get_copilot_job_status`, `request_copilot_review`). |
| D8 | **Deliver all five milestone plans upfront** for review, then implement sequentially. M0 is execution-ready; M1–M4 are concrete roadmaps refined with `writing-plans` just before each is built. | User preference; avoids stale fine-grained detail for later milestones. |

---

## 2. Agent Model (7 agents)

```
PHASE 1 (collaborative, once per project)
  1. PM Agent              idea  ──▶ PRD (Confluence)              [human approves]
  2. Architecture Agent    PRD   ──▶ Arch plan (Confluence)        [human approves]
                                 ──▶ GitHub repo + docs/ARCHITECTURE.md + README + skeleton
  3. Jira Structuring      PRD   ──▶ Epics + Stories + Tasks (Jira) [human approves epics, then stories]

PHASE 2 (event-driven, per ticket)
  4. Planning Agent        Jira ticket ──▶ rich GitHub issue ──▶ assign_copilot_to_issue
     (GitHub Copilot)      issue       ──▶ branch + code + tests + PR   (autonomous, not our agent)
  5. QA Agent              PR ──▶ clone + pytest + ruff ──▶ pass | (comment + re-assign Copilot, retry ≤3)
  6. Review Agent          PR ──▶ acceptance-criteria + arch-compliance checklist ──▶ merge | request changes
  7. Jira Update Agent     merged ──▶ transition Jira to Done + comment (PR link, cycle time)
```

## 3. Per-Agent Scoped Tool Matrix

Tool names are the exact MCP tool identifiers in this environment (from `agents/*.md`).

| Agent | Confluence | Jira | GitHub | Local-exec (ours) |
|---|---|---|---|---|
| **PM** | search, get_page, create_page, update_page, add_comment | — | — | — |
| **Architecture** | get_page, create_page, add_label | — | get_me, create_repository, push_files, create_or_update_file, get_file_contents | — |
| **Jira Structuring** | get_page, get_page_children, create_page, add_label | list_projects, get_project, get_field_options, create_issue, update_issue, add_comment, get_issue_link_types | — | — |
| **Planning** | get_page | get_issue | get_file_contents, list_branches, issue_write, assign_copilot_to_issue, get_copilot_job_status | — |
| **QA** | — | get_issue | pull_request_read, add_issue_comment, assign_copilot_to_issue (retry) | clone, run_tests, run_linter, parse_logs |
| **Review** | get_page | get_issue | pull_request_read, pull_request_review_write, merge_pull_request, request_copilot_review | — |
| **Jira Update** | — | get_transitions, transition_issue, add_comment | pull_request_read | — |

## 4. Known MCP Constraints (from `agents/tech-lead-breakdown.md`)

- **Jira MCP cannot set a sub-task `parent`.** Create issue type **Task** (not Sub-task) and link to the parent Story via a comment listing the related Task keys.
- **Jira MCP has no `create_issue_link`.** Document dependencies between issues via comments; formal links are a manual UI step.

---

## 5. Milestones (verification gate per milestone)

| M | Scope | Done when |
|---|---|---|
| **M0** | Foundation & MCP wiring: FastAPI app, config, `LLMClient`, Postgres + SQLAlchemy + Alembic (4 tables), `MultiServerMCPClient` → 3 MCP servers, tool-logging callback, local-exec utility (clone/pytest/ruff). | App boots, `/health` 200, migrations apply, MCP client lists tools from each server, a cloned repo runs pytest, a tool call writes an `agent_execution_logs` row. |
| **M1** | Phase 1 pipeline: project state machine, `POST /projects` + chat + approvals endpoints, PM + Architecture + Jira Structuring agents. | Idea → PRD → arch plan + live repo → epics/stories created in **real** Confluence/Jira/GitHub, gated by human approvals. |
| **M2** | Phase 2 pipeline: ticket state machine + retry cap, Jira/GitHub webhooks + dispatcher, Planning + QA + Review + Jira Update agents, Copilot loop. | A Jira ticket → AI_READY → Copilot PR → QA → review → merge → Jira Done on a real repo, with state transitions logged. |
| **M3** | Frontend dashboard: Next.js chat, approval views, execution monitor, agent log viewer, API client. | All Phase 1 approvals and Phase 2 monitoring are driveable from the UI. |
| **M4** | E2E integration, hardening & demo: the 15-step Definition of Done, error/escalation paths, env/setup docs, observability polish. | The full idea → merged-PR → Jira-Done demo runs end to end; metrics captured. |

---

## 6. Open Dependencies / Risks

- **Backend ↔ MCP server connection config.** The FastAPI backend runs as a separate process from Claude Code, so it needs its own connection details (remote URLs or stdio launch commands) + tokens for the Confluence/Jira/GitHub MCP servers. Resolved in M0 via `MCP_SERVERS` config. If the GitHub MCP is the remote hosted server, the PAT scopes must include Copilot assignment.
- **Copilot coding-agent availability** on the target repo/org (requires the feature enabled). Confirmed available (D7); verified again in M2's first smoke test.
- **Jira workflow** must have an "AI Ready" status and a transition to "Done" matching the webhook trigger. Verified in M1/M2 against the real Jira project.
