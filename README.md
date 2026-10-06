# sdlc-ai-orchestrator (AI Engineering Orchestrator, "AEO")

Design and specification for a human-in-the-loop, multi-agent system that automates the software development lifecycle across Confluence, Jira and GitHub. This repository currently holds the academic project documents, the full MVP implementation spec and four Claude Code agent definitions; the backend/frontend described in the spec are not yet in the repo.

## Problem
Teams lose time on manual hand-offs: PRD in Confluence, architecture design, Jira epics/tickets, then code in GitHub. AEO treats those platforms as tools operated by specialised AI agents under human approval.

## Planned system (from IMPLEMENTATION_SPEC.md v1.1)
- **Phase 1, project initialisation**: agents produce a PRD, technical architecture and repository template, with human approval gates.
- **Phase 2, recurrent execution**: an event-driven orchestrator reacts to Jira tickets, plans the work, delegates code authoring to GitHub Copilot (via a detailed issue), runs tests/lint (pytest/ruff via subprocess) and reviews.
- Chosen stack: monorepo; FastAPI backend; LangGraph agents; abstract `LLMClient` (Anthropic or OpenAI); Supabase/PostgreSQL state with SQLAlchemy async and Alembic; Next.js 14 + Zustand dashboard; MCP servers for Confluence, Jira, GitHub and local execution; Python 3.11, Node 20.
- Env var names listed in the spec: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `LLM_PROVIDER`, `LLM_MODEL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `DATABASE_URL`, `CONFLUENCE_*`, `JIRA_*`, `GITHUB_PAT`, `GITHUB_DEFAULT_ORG`, `WEBHOOK_SECRET`.

## What is in the repo
```
IMPLEMENTATION_SPEC.md          # full MVP build spec (monorepo layout, stack, setup, env vars)
project.md / project_detail.md  # MCA project synopsis and detailed system design
MCA Final project plan.docx, MCA_Synopsis_AkshayKumarBM.docx
agents/
  product-manager.md            # requirements and PRD agent (Confluence tools)
  solution-architecture.md      # architecture design agent
  tech-lead-breakdown.md        # epics/tickets breakdown agent
  agent-architect.md            # agent that designs agents
CLAUDE.md                       # general LLM coding behaviour guidelines
```

## Limitations / status
- Specification and agent prompts only; no runnable orchestrator, tests or Docker setup committed.
- Project synopsis still has template placeholders (USN, guide name).
- Spec evolved (v1.1 replaced the custom Dev Agent with GitHub Copilot).
