# M4 — End-to-End Integration, Hardening & Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: re-run superpowers:writing-plans to expand into bite-sized steps before building. Concrete roadmap per **D8**. This milestone wires everything into the single demo that defines "done" for the MVP.

**Goal:** Make the whole system run end-to-end without human intervention beyond the defined approval gates — the 15-step Definition of Done from `IMPLEMENTATION_SPEC.md §11` — and harden the error/escalation paths, observability, and setup docs around it.

**Architecture:** No new subsystems. M4 connects M0–M3, closes gaps found during integration, and adds the operational glue (docker-compose, env docs, metrics capture). The deliverable is a reproducible demo + the docs to run it.

**Tech Stack:** Same as M0–M3 + `docker-compose` for local orchestration.

**Depends on:** M0, M1, M2, M3 all individually verified.

---

## File Structure

| File | Responsibility |
|---|---|
| `docker-compose.yml` | backend + frontend + Postgres for local run |
| `backend/app/api/projects.py` (modify) | metrics endpoint: cycle time, retries, token usage per ticket |
| `backend/app/orchestrator/metrics.py` | compute success metrics from logs/executions |
| `README.md` (modify) / `docs/RUNBOOK.md` | setup, env vars, Jira/GitHub webhook + Copilot prerequisites, demo script |
| `backend/tests/integration/test_full_e2e.py` | the 15-step flow as an automated harness (mocked MCP) |

---

## Task 1: Compose + environment wiring

**Files:** Create `docker-compose.yml`; modify `README.md`/`docs/RUNBOOK.md`

- [ ] `docker-compose.yml`: `postgres:16`, `backend` (uvicorn, env_file), `frontend` (next dev, `NEXT_PUBLIC_API_URL`). Backend depends_on postgres; runs `alembic upgrade head` on start.
- [ ] RUNBOOK: required env (`DATABASE_URL`, `LLM_*`, `MCP_SERVERS`, `WEBHOOK_SECRET`), how to register Jira + GitHub webhooks pointing at the backend, GitHub Copilot coding-agent prerequisite (enabled on repo/org; PAT scopes), and the demo script.

**Verify:** `docker compose up` brings up all three; `/health` and the dashboard load; migrations applied.
**Commit:** `chore(m4): docker-compose + runbook`

---

## Task 2: Wire approval-resolution → dispatcher across phases

**Files:** Modify `app/orchestrator/dispatcher.py`, `app/api/approvals.py`

- [ ] Ensure resolving each approval triggers the correct next action end-to-end: PRD→Architecture; Architecture→(repo provision + Jira structuring); Epics→Stories; Stories→`PHASE_1_COMPLETE`. Verify the `ARCHITECTURE_APPROVED → (REPO_BOOTSTRAPPING, JIRA_STRUCTURING)` fan-out and that `PHASE_1_COMPLETE` is only set once both branches finish.

**Tests:** `test_phase1_fanout_completes_when_both_done`, `test_approval_resolution_triggers_next_agent`.
**Commit:** `feat(m4): cross-phase approval→dispatch wiring`

---

## Task 3: Error & escalation paths

**Files:** Modify agents + dispatcher; Test `tests/test_error_paths.py`

- [ ] **MCP/tool unavailable:** an agent's tool error moves the unit to `ESCALATED` (ticket) or surfaces a clear API error (project) — never a silent failure (NFR: graceful degradation).
- [ ] **Retry cap:** confirm QA/Review re-assignment stops at 3 and creates an ESCALATION approval with the full failure log; the monitor shows `ESCALATED`.
- [ ] **Webhook idempotency:** duplicate `PR_OPENED`/`PR_MERGED` don't double-run agents.

**Tests:** `test_tool_failure_escalates_ticket`, `test_retry_cap_creates_escalation`, `test_duplicate_webhook_is_idempotent`.
**Commit:** `feat(m4): hardened error and escalation paths`

---

## Task 4: Success-metrics capture

**Files:** Create `app/orchestrator/metrics.py`; modify `app/api/projects.py`; Test `tests/test_metrics.py`

- [ ] Compute from `ticket_executions` + `agent_execution_logs`: cycle time (AI_READY→MERGED), retries per ticket, token usage per agent, % tickets merged without human coding, escalation rate. Expose `GET /projects/{id}/metrics`.

**Tests:** `test_cycle_time_computed`, `test_token_usage_aggregated_per_agent`.
**Commit:** `feat(m4): success metrics endpoint`

---

## Task 5: The 15-step E2E harness (mocked MCP)

**Files:** Create `tests/integration/test_full_e2e.py`

- [ ] Automate the Definition of Done as one test with mocked MCP tools + simulated webhooks + real Postgres: idea → PRD (save+approve) → architecture (approve) → repo created + arch doc injected → epics (approve) → stories/tasks (approve) → `PHASE_1_COMPLETE` → move ticket to AI Ready → issue + Copilot assign → PR opened → QA pass → review merge → Jira Done. Assert every state transition, all four project links set, and metrics populated.

**Commit:** `test(m4): full 15-step e2e harness`

---

## Task 6: M4 VERIFICATION GATE — live demo

- [ ] **Live end-to-end run against real Confluence/Jira/GitHub + Copilot**, executing the 15 steps from `IMPLEMENTATION_SPEC.md §11` with only the four approval gates as human input. Capture on the run:
  1. Total cycle time AI Ready → Merged.
  2. Retry count for the demo ticket.
  3. Token usage per agent.
  4. All four Confluence/Jira/GitHub links populated in the DB and visible in the dashboard.
- [ ] Record results in `docs/RUNBOOK.md` (demo log section).

**Commit:** `docs(m4): record live demo results — MVP complete`

---

## Self-Review (M4)

- **Spec coverage:** the 15-step DoD (§11) is automated in Task 5 and run live in Task 6; NFRs (graceful degradation, retry cap, observability, metrics) in Tasks 3–4; setup/runbook in Task 1.
- **No new subsystems** — M4 is integration + hardening only, matching the milestone's purpose (avoids scope creep).
- **Metrics** map to `IMPLEMENTATION_SPEC.md §16` targets, so the demo can report against them.
- **Open dependency check (final):** Jira "AI Ready" status + webhook delivery to the backend (public URL or tunnel) + Copilot enabled — all validated in Task 1's runbook and the Task 6 live run.
- **Refine before build:** finalize metric definitions and the compose health-checks against the actual M1/M2 schema at execution time.
