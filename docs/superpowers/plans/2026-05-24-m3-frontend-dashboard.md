# M3 — Frontend Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: re-run superpowers:writing-plans to expand into bite-sized steps before building; consider superpowers:frontend-design for component styling. Concrete roadmap per **D8**. **Verify UI in a browser** before claiming done (per project guidelines).

**Goal:** A single-user Next.js dashboard that drives every human touchpoint: chat with the PM Agent, approve PRD/Architecture/Epics/Stories, and monitor Phase 2 ticket executions with live state + per-agent logs.

**Architecture:** Next.js 14 App Router (TypeScript). A thin typed API client wraps the backend REST endpoints from M1/M2. Server components fetch initial state; client components poll for live updates (execution monitor, chat). No auth (MVP, single user).

**Tech Stack:** Next.js 14, TypeScript, Zustand (light client state), Tailwind (or CSS modules), `fetch`. No SSR auth.

**Depends on:** M1 endpoints (`/projects`, `/projects/{id}/chat`, `/approvals/*`) and M2 (`/projects/{id}/executions`, ticket detail).

---

## File Structure

| File | Responsibility |
|---|---|
| `frontend/src/lib/api.ts` | Typed client for all backend endpoints |
| `frontend/src/lib/types.ts` | Shared TS types (Project, Approval, TicketExecution, AgentLog) |
| `frontend/src/app/page.tsx` | Project list + create form |
| `frontend/src/app/projects/[id]/page.tsx` | Project dashboard: status, links, monitor |
| `frontend/src/app/projects/[id]/chat/page.tsx` | PM Agent chat |
| `frontend/src/app/projects/[id]/approve/[approvalId]/page.tsx` | Approval view |
| `frontend/src/app/projects/[id]/tickets/[executionId]/page.tsx` | Ticket detail + logs |
| `frontend/src/components/ChatInterface.tsx` | Message list + input |
| `frontend/src/components/ApprovalCard.tsx` | Renders PRD/Arch/Epic/Story + approve/reject |
| `frontend/src/components/ExecutionMonitor.tsx` | Polling table of ticket states |
| `frontend/src/components/AgentLogViewer.tsx` | Expandable per-agent log rows |
| `frontend/tests/...` | Component tests (Vitest/RTL) where useful |

---

## Task 1: Scaffold + API client + types

**Files:** Create `frontend/` (Next 14 app), `src/lib/types.ts`, `src/lib/api.ts`

- [ ] `npx create-next-app@14 frontend --ts --app --tailwind` (or equivalent), set `NEXT_PUBLIC_API_URL`.
- [ ] `types.ts`: mirror backend response shapes (`Project {id,name,status,confluence_prd_url,confluence_arch_url,github_repo_url,jira_project_key}`, `Approval {id,approval_type,payload,status}`, `TicketExecution {id,jira_ticket_key,status,retry_count,current_agent,github_pr_url}`, `AgentLog {agent_name,skill_requested,status,token_usage,duration_ms,created_at}`).
- [ ] `api.ts`: typed functions — `createProject`, `getProject`, `sendChatMessage`, `getPendingApprovals`, `approveRequest(id,feedback?)`, `rejectRequest(id,feedback)`, `getExecutions(projectId)`, `getExecutionLogs(executionId)`.

**Verify:** `npm run dev` boots; `api.ts` typechecks (`tsc --noEmit`).
**Commit:** `feat(m3): scaffold next app + typed API client`

---

## Task 2: Project list + create

**Files:** `src/app/page.tsx`

- [ ] List projects (status badge + links), a create form (`name`, optional `confluence_space_key`) → `createProject` → navigate to `/projects/[id]/chat`.

**Verify (browser):** create a project, land on chat page; new project appears in list with `INITIALIZED`/`PRD_DRAFTING`.
**Commit:** `feat(m3): project list + create`

---

## Task 3: PM chat interface

**Files:** `src/app/projects/[id]/chat/page.tsx`, `src/components/ChatInterface.tsx`

- [ ] Message list + input; on submit call `sendChatMessage`, append assistant reply. When the response indicates a PRD approval is pending, surface a banner linking to the approval view.

**Verify (browser):** hold a short back-and-forth; confirm assistant replies render and the "PRD ready for approval" banner appears after the agent saves the PRD.
**Commit:** `feat(m3): PM chat interface`

---

## Task 4: Approval views

**Files:** `src/app/projects/[id]/approve/[approvalId]/page.tsx`, `src/components/ApprovalCard.tsx`

- [ ] Render by `approval_type`: PRD (markdown), Architecture (stack/folders/schema), Epics (list), Stories (per-epic list with acceptance criteria). Approve (optional feedback) / Reject (required feedback) → call API → on success route back to dashboard.

**Verify (browser):** approve a PRD and an Architecture; reject one with feedback and confirm the agent re-engages (re-drafts). Reject without feedback is blocked client-side.
**Commit:** `feat(m3): approval views (PRD/arch/epics/stories)`

---

## Task 5: Project dashboard + execution monitor

**Files:** `src/app/projects/[id]/page.tsx`, `src/components/ExecutionMonitor.tsx`

- [ ] Dashboard: project status, the four links (PRD, Arch, Repo, Jira), pending-approvals list.
- [ ] `ExecutionMonitor`: polls `getExecutions` every ~3s; table of `jira_ticket_key`, `status`, `current_agent`, `retry_count`, PR link; row → ticket detail.

**Verify (browser):** with a Phase 2 ticket running (or seeded), watch states advance (`AI_READY → … → JIRA_UPDATED`) and retry count update live.
**Commit:** `feat(m3): project dashboard + live execution monitor`

---

## Task 6: Ticket detail + agent log viewer

**Files:** `src/app/projects/[id]/tickets/[executionId]/page.tsx`, `src/components/AgentLogViewer.tsx`

- [ ] Ticket detail: state timeline, issue/PR links, retry history. `AgentLogViewer`: expandable rows per `agent_execution_logs` entry (agent, tool, status, tokens, duration, timestamps).

**Verify (browser):** open a completed ticket; logs show the Planning→QA→Review→Jira-Update chain with token/duration data.
**Commit:** `feat(m3): ticket detail + agent log viewer`

---

## Task 7: M3 verification gate

- [ ] **Browser walkthrough (real backend):** from the UI alone — create a project, chat to a PRD, approve PRD + Architecture, approve Epics + Stories, then watch a ticket run in the monitor and inspect its logs. Confirm no console errors and all four project links open.

**Commit:** `test(m3): dashboard end-to-end walkthrough`

---

## Self-Review (M3)

- **Spec coverage:** the four dashboard capabilities from `IMPLEMENTATION_SPEC.md §9` (chat, approvals, execution monitor, log viewer) map to Tasks 3–6; API client (Task 1) matches M1/M2 endpoints exactly.
- **Reject requires feedback** — enforced client-side (Task 4) and server-side (M1 Task 3).
- **Live updates** via polling (simple, MVP). WebSockets/streaming are a future enhancement, not now (YAGNI).
- **Browser verification** is mandatory per project guidelines — every task above ends with a browser check, not just a passing build.
- **Refine before build:** confirm exact backend response field names against the running M1/M2 API before finalizing `types.ts`.
