# M2 — Phase 2 Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: re-run superpowers:writing-plans to expand this roadmap into bite-sized TDD steps **immediately before building**, then use superpowers:subagent-driven-development. Concrete roadmap; micro-steps finalized at execution time per **D8**.

**Goal:** Turn a Jira ticket marked "AI Ready" into merged, reviewed code — autonomously — via the event-driven loop: Planning Agent writes a rich GitHub issue and assigns Copilot; Copilot opens a PR; QA clones+tests; Review checks acceptance criteria and merges; Jira Update closes the ticket. Failures retry through Copilot up to 3 times, then escalate to a human.

**Architecture:** Webhooks (Jira status change, GitHub PR/CI/merge) hit the orchestrator, which advances the ticket state machine and dispatches the right agent. Agents use scoped MCP tools (Planning/QA/Review/Jira-Update) + the M0 `local_exec` for tests. Retry state lives on `ticket_executions.retry_count`; the cap is enforced by the dispatcher.

**Tech Stack:** Same as M0/M1 + webhook HMAC verification (`hmac`/`hashlib`).

**Depends on:** M0 (foundation, MCP, local-exec) and M1 (a `PHASE_1_COMPLETE` project with a repo + Jira backlog).

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/app/orchestrator/ticket_states.py` | `TICKET_TRANSITIONS`, `assert_transition`, retry helpers |
| `backend/app/orchestrator/tickets.py` | `TicketExecutionService`: create, advance, increment_retry, escalate |
| `backend/app/orchestrator/ticket_dispatcher.py` | event → agent routing + retry/escalation policy |
| `backend/app/api/webhooks.py` | `POST /webhooks/jira`, `POST /webhooks/github` + HMAC verify |
| `backend/app/core/webhook_security.py` | `verify_signature(body, header, secret)` |
| `backend/app/agents/planning.py` | Planning Agent (rich issue + assign Copilot + poll) |
| `backend/app/agents/qa.py` | QA Agent (clone, test, lint, error report, retry) |
| `backend/app/agents/review.py` | Review Agent (checklist + merge) |
| `backend/app/agents/jira_update.py` | Jira Update Agent (transition + comment) |
| `backend/app/agents/issue_template.py` | Copilot-optimized GitHub issue renderer |
| `backend/tests/...` | Per-module tests + a Phase-2 integration test |

---

## Task 1: Ticket state machine

**Files:** Create `app/orchestrator/ticket_states.py`; Test `tests/test_ticket_states.py`

```python
TICKET_TRANSITIONS: dict[str, list[str]] = {
    "AI_READY":         ["PLANNING"],
    "PLANNING":         ["COPILOT_ASSIGNED"],
    "COPILOT_ASSIGNED": ["IN_QA"],
    "IN_QA":            ["READY_TO_MERGE", "COPILOT_RETRY", "ESCALATED"],
    "COPILOT_RETRY":    ["IN_QA", "ESCALATED"],
    "READY_TO_MERGE":   ["MERGED"],
    "MERGED":           ["JIRA_UPDATED"],
}
MAX_RETRIES = 3
```

Plus `assert_transition(src, dst)` (raises `InvalidTransition`) and `should_escalate(retry_count) -> bool` (`retry_count >= MAX_RETRIES`).

**Tests:** `test_happy_path_transitions`, `test_qa_can_go_three_ways`, `test_should_escalate_at_cap`.
**Commit:** `feat(m2): ticket state machine + retry cap`

---

## Task 2: TicketExecutionService

**Files:** Create `app/orchestrator/tickets.py`; Test `tests/test_ticket_service.py`

```python
class TicketExecutionService:
    async def create(self, project_id, jira_ticket_key) -> TicketExecution      # status AI_READY
    async def get_by_jira_key(self, jira_ticket_key) -> TicketExecution | None
    async def get_by_pr_url(self, pr_url) -> TicketExecution | None              # for GitHub webhooks
    async def advance(self, ticket_id, dst, *, current_agent=None) -> TicketExecution  # guarded
    async def increment_retry(self, ticket_id) -> int                            # returns new count
    async def set_links(self, ticket_id, *, issue_url=None, pr_url=None, branch=None) -> TicketExecution
    async def escalate(self, ticket_id, error: str) -> TicketExecution           # ESCALATED + ApprovalService(type=ESCALATION)
```

**Tests:** `test_create_ai_ready`, `test_advance_guarded`, `test_increment_retry`, `test_escalate_creates_approval`.
**Commit:** `feat(m2): ticket execution service`

---

## Task 3: Webhook security + endpoints

**Files:** Create `app/core/webhook_security.py`, `app/api/webhooks.py`; Test `tests/test_webhooks.py`

`verify_signature(body: bytes, signature_header: str, secret: str) -> bool` using HMAC-SHA256 (GitHub `X-Hub-Signature-256: sha256=...`). For Jira (no native HMAC on all plans), accept a shared-secret query token or a configured header; document the chosen mechanism.

Endpoints translate raw events → internal events, then call the ticket dispatcher:

```
POST /webhooks/jira    issue status -> "AI Ready"     => event JIRA_AI_READY(jira_key, project)
POST /webhooks/github  pull_request opened            => event PR_OPENED(pr_url, branch, issue_ref)
POST /webhooks/github  check_suite/CI completed       => event CI_RESULT(pr_url, conclusion)
POST /webhooks/github  pull_request closed+merged     => event PR_MERGED(pr_url)
```

Reject (401) on bad signature; return 202 on accepted (work runs in background).

**Tests:** `test_rejects_bad_signature`, `test_jira_ai_ready_creates_ticket_execution`, `test_github_pr_opened_routes_to_qa` (mock dispatcher).
**Commit:** `feat(m2): webhook endpoints with signature verification`

---

## Task 4: Copilot-optimized issue template

**Files:** Create `app/agents/issue_template.py`; Test `tests/test_issue_template.py`

Pure function `render_issue(ctx: PlanningContext) -> str` producing the markdown from `IMPLEMENTATION_SPEC.md §8.5` (Task title, Jira/Epic refs, branch name, Context, **Architecture Constraints**, filtered repo tree, Files-to-create/modify table, DB changes, API contract, **Acceptance Criteria checklist**, dependencies). Keep it deterministic and testable (no LLM in this function).

**Tests:** `test_render_includes_acceptance_criteria_and_branch`, `test_render_lists_files_table`.
**Commit:** `feat(m2): copilot-optimized issue renderer`

---

## Task 5: Planning Agent

**Files:** Create `app/agents/planning.py`; Test `tests/test_planning_agent.py`

**Trigger:** `JIRA_AI_READY`. **Graph:** `fetch_jira_ticket → fetch_arch (docs/ARCHITECTURE.md via get_file_contents) → analyze_repo_tree (list_branches/get_file_contents) → build_plan → render_issue → issue_write(create) → assign_copilot_to_issue → (poll get_copilot_job_status until PR opened OR rely on PR_OPENED webhook)`.

State: `ticket_execution_id, jira_ticket_key, arch_plan, repo_tree, github_issue_url, copilot_job_id`.
On issue+assign: `TicketExecutionService.advance(PLANNING → COPILOT_ASSIGNED)`, store `github_issue_url`. The orchestrator then waits for the `PR_OPENED` webhook (preferred) to move to `IN_QA`; polling `get_copilot_job_status` is a fallback for environments without webhooks.

**Constraint:** all file paths in the issue must exist within (or be new files under) the approved architecture folder structure — validate against the repo tree before creating the issue.

**Tests (mock Jira/GitHub tools):**
- `test_planning_creates_issue_then_assigns_copilot` (order: `issue_write` before `assign_copilot_to_issue`)
- `test_planning_advances_to_copilot_assigned`
- `test_planning_rejects_paths_outside_arch` (a planned path not under the skeleton → raises/repairs)

**Commit:** `feat(m2): planning agent — issue + copilot assignment`

---

## Task 6: QA Agent (test + retry loop)

**Files:** Create `app/agents/qa.py`; Test `tests/test_qa_agent.py`

**Trigger:** `PR_OPENED`. **Graph:** `read_pr_diff (pull_request_read) → fetch_acceptance_criteria (jira_get_issue) → clone_branch → install test deps (pytest, pytest-json-report, ruff) → run_linter → run_tests → evaluate`:
- **Pass:** comment results on PR (`add_issue_comment`) → `advance(IN_QA → READY_TO_MERGE)` → trigger Review.
- **Fail & `retry_count < 3`:** LLM builds a structured error report (`{failing_tests, lint_violations, root_cause_hypothesis, suggested_fix}`), `add_issue_comment` on the **PR** with the report, `increment_retry`, `assign_copilot_to_issue` again, `advance(IN_QA → COPILOT_RETRY)`. Copilot pushes a fix commit → CI/PR event → back to `IN_QA`.
- **Fail & `retry_count == 3`:** `TicketExecutionService.escalate(...)` → `ESCALATED` + ESCALATION approval with full log.

> Implements the M0 note: QA installs `pytest-json-report` in the cloned repo's env before `run_tests` so `parse_pytest_report` has a report file.

**Tests (mock GitHub + local_exec):**
- `test_qa_pass_advances_to_ready_to_merge`
- `test_qa_fail_under_cap_reassigns_copilot_and_increments_retry`
- `test_qa_fail_at_cap_escalates`

**Commit:** `feat(m2): qa agent with copilot retry loop`

---

## Task 7: Review Agent

**Files:** Create `app/agents/review.py`; Test `tests/test_review_agent.py`

**Trigger:** QA pass (or `CI_RESULT` success). **Graph:** `read_pr_diff → fetch_acceptance_criteria (jira_get_issue) → fetch_arch (docs/ARCHITECTURE.md) → run_checklist → decide`:
- Checklist: acceptance-criteria coverage, **architecture compliance** (no new top-level dirs / tech-stack drift — this is the D5 post-hoc enforcement), no hardcoded secrets, no dead code, PR references the Jira ticket.
- **All pass:** `pull_request_review_write(APPROVE)` → `merge_pull_request` → `advance(READY_TO_MERGE → MERGED)` → trigger Jira Update.
- **Issues:** post structured review comments (`pull_request_review_write` REQUEST_CHANGES), optionally `request_copilot_review`, `increment_retry`, re-assign Copilot, back toward `IN_QA`/`COPILOT_RETRY` (respect the cap).

**Tests (mock GitHub tools):**
- `test_review_merges_when_all_checks_pass`
- `test_review_requests_changes_on_arch_violation` (no merge call)

**Commit:** `feat(m2): review agent — checklist + merge`

---

## Task 8: Jira Update Agent

**Files:** Create `app/agents/jira_update.py`; Test `tests/test_jira_update_agent.py`

**Trigger:** `PR_MERGED`. **Graph:** `fetch_execution_record → jira_get_transitions → jira_transition_issue(Done) → jira_add_comment` with the summary block (PR link, branch, test count, cycle time AI_READY→MERGED computed from `created_at`/`updated_at`). `advance(MERGED → JIRA_UPDATED)`.

**Tests (mock Jira tools):**
- `test_jira_update_transitions_to_done_and_comments`
- `test_cycle_time_in_comment`

**Commit:** `feat(m2): jira update agent — close the loop`

---

## Task 9: Ticket dispatcher (event routing + retry policy)

**Files:** Create `app/orchestrator/ticket_dispatcher.py`; Test `tests/test_ticket_dispatcher.py`

Maps internal events → agent runs and owns the retry/escalation policy:

```
JIRA_AI_READY  -> create ticket_execution (AI_READY) + run Planning Agent
PR_OPENED      -> advance to IN_QA + run QA Agent
CI_RESULT pass -> run Review Agent
CI_RESULT fail -> (handled inside QA after its own run) — guard against double-trigger
PR_MERGED      -> run Jira Update Agent
```

Retry/escalation: the dispatcher checks `should_escalate(retry_count)` before re-assigning Copilot.

**Tests:** `test_routes_each_event`, `test_dispatcher_escalates_at_cap`, `test_no_double_qa_on_duplicate_webhook` (idempotency by PR url + state guard).
**Commit:** `feat(m2): ticket dispatcher with retry/escalation policy`

---

## Task 10: Phase 2 integration test + real-services verification gate

**Files:** Create `tests/integration/test_phase2_flow.py`

- [ ] **Integration test (mocked MCP + simulated webhooks, real Postgres):** seed a ticket → fire `JIRA_AI_READY` → assert issue created + Copilot assigned + state `COPILOT_ASSIGNED` → fire `PR_OPENED` → QA passes (mock local_exec) → Review merges → fire `PR_MERGED` → Jira Update → final state `JIRA_UPDATED`. Then a **failure-path** test: QA fails 3× → `ESCALATED` + ESCALATION approval row.

- [ ] **M2 VERIFICATION GATE — real services (uses the M1 repo + Jira):**
  1. Move a real Jira Story to **"AI Ready"** → Planning Agent creates a **real GitHub issue** and assigns **Copilot**.
  2. Copilot opens a **real PR**; QA clones, runs pytest+ruff, comments results.
  3. Review approves + **merges the PR**; Jira ticket transitions to **Done** with the summary comment + PR link.
  4. `agent_execution_logs` shows the full chain; `ticket_executions.status == JIRA_UPDATED`; cycle time recorded.

**Commit:** `test(m2): phase 2 integration flow + verification`

---

## Self-Review (M2)

- **Spec coverage:** FR-08..FR-19 (AI Ready trigger, issue creation, branch/code/PR via Copilot, tests, ≤3 retries, escalation, arch enforcement, acceptance-criteria review, auto-merge, Jira Done + PR link) map to Tasks 1–10. Arch enforcement = Review Agent (D5).
- **Copilot loop:** Planning assigns (Task 5); QA re-assigns on failure (Task 6); cap enforced by dispatcher (Task 9). Matches the confirmed Copilot behavior (assign → autonomous PR → iterate from comments).
- **Idempotency:** webhooks may fire twice — Task 9 guards by PR url + current state.
- **Type consistency:** `TicketExecutionService` method names used identically across Tasks 5–9; events (`JIRA_AI_READY`, `PR_OPENED`, `CI_RESULT`, `PR_MERGED`) defined once in Task 3 and consumed in Task 9.
- **Refine before build:** expand agent graph node functions (Tasks 5–8) to bite-sized TDD steps via writing-plans at execution time.
