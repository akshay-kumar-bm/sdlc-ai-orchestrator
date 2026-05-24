
**JAIN**
**DEEMED-TO-BE UNIVERSITY**
**CENTRE FOR DISTANCE AND ONLINE EDUCATION**

**SYNOPSIS ON**
**AI-POWERED SOFTWARE DEVELOPMENT LIFECYCLE (SDLC) AUTOMATION SYSTEM**

Project-I Report submitted to JAIN (Deemed-to-be University)

By
**NAME: AKSHAY KUMAR B M**
**USN: [Insert Your USN Here]**
**SEMESTER: II**
**PROGRAM: MCA**

Under the guidance of
**[Insert Guide Name]**
**[Insert Designation]**

**Bengaluru**
**2026**

---

### TABLE OF CONTENTS

Abstract
**Chapter 1: Introduction**
1.1 Background of the Study
1.2 Evolution from Coding Assistants to AI Orchestration
1.3 Problem Domain: Manual Handoffs vs. Autonomous Workflows
1.4 Motivation for the Project
**Chapter 2: Literature Review & Problem Statement**
2.1 Review of Existing Solutions
2.2 Gaps in Current Industry Practices
2.3 Problem Statement
2.4 Significance of the Study
**Chapter 3: Objectives & Scope**
3.1 Primary Objective
3.2 Specific Objectives
3.3 Scope of the Project
3.4 Limitations
**Chapter 4: Methodology & System Architecture**
4.1 Research Methodology
4.2 System Architecture Overview
4.3 Technology Stack Justification
**Chapter 5: Proposed System Modules**
5.1 Module 1: Project Initialization & PRD Generation
5.2 Module 2: Repository Bootstrap & Task Structuring
5.3 Module 3: Event-Driven Orchestrator & State Machine
5.4 Module 4: Autonomous Execution Loop
5.5 Module 5: Code Review & Traceability
**Chapter 6: Feasibility Study**
6.1 Technical Feasibility
6.2 Operational Feasibility
**Chapter 7: Expected Outcomes**
**Chapter 8: Project Timeline**
**References**

---

### ABSTRACT

The traditional Software Development Life Cycle (SDLC) requires significant manual effort for administrative and transitional tasks, such as translating abstract ideas into Product Requirements Documents (PRDs), structuring Jira tickets, and writing boilerplate code. While current AI tools assist individual developers via inline code generation, they fail to orchestrate the entire SDLC with enterprise governance. This project proposes an AI Engineering Orchestrator utilizing a human-in-the-loop, multi-agent architecture. The system natively integrates with Confluence, Jira, and GitHub using Large Language Model (LLM) SDKs. It operates in two phases: Phase 1 (Project Initialization), where agents generate structured PRDs, technical architectures, and repository templates; and Phase 2 (Recurrent Execution), an event-driven orchestrator that automatically plans, codes, tests, and reviews code upon Jira ticket creation. Built utilizing a Next.js frontend, a FastAPI backend orchestrator, and Supabase for state management, this system bridges the gap between individual AI coding assistants and enterprise-level engineering automation, reducing manual overhead while strictly adhering to human-approved architectural constraints.

---

### CHAPTER 1: INTRODUCTION

**1.1 Background of the Study**
Modern software engineering teams dedicate approximately 30-40% of their operational cycles to project management, codebase synchronization, and documentation rather than core feature development. Transitioning from a product concept to a deployable codebase requires manual translation across multiple enterprise tools, leading to inefficiencies, context loss, and slower time-to-market.

**1.2 Evolution from Coding Assistants to AI Orchestration** Traditional software automation focused on CI/CD pipelines to deploy static binaries. The emergence of Generative AI introduced Copilots capable of inline code completion. However, the industry is now shifting toward "Agentic AI"—software that can reason, plan, and execute multi-step engineering tasks autonomously across various platforms.

**1.3 Problem Domain: Manual Handoffs vs. Autonomous Workflows** The core engineering challenge lies in bridging the gaps between discrete systems. A Product Manager writes a PRD in Confluence, an Architect designs a system, an Agile Coach creates Jira Epics, and a Developer writes code in GitHub. These manual handoffs are error-prone. This project addresses the conflict by building a "Control Plane" that treats these enterprise platforms as tools to be autonomously operated by specialized AI agents under human supervision.

**1.4 Motivation for the Project**
The motivation stems from the bottleneck observed in real-world engineering teams where scaling the output requires linearly scaling the headcount. By orchestrating AI agents to handle boilerplate repository setup, unit test generation, and Jira state updates, technical teams can focus entirely on high-level logic, security, and product-market fit.

---

### CHAPTER 2: LITERATURE REVIEW & PROBLEM STATEMENT

**2.1 Review of Existing Solutions**
Current literature highlights a gap in macro-level workflow automation. Tools like GitHub Copilot and Cursor excel at micro-level code generation but operate within isolated developer environments. Existing multi-agent frameworks lack the contextual memory required to autonomously map a Confluence PRD to Jira Epics, and subsequently execute those tickets in GitHub without constant human prompting.

**2.2 Gaps in Current Industry Practices**
Despite the availability of LLMs, the "orchestration infrastructure" lags significantly behind:

* **No Unified Context:** Agents do not share a synchronized "Architecture Memory" across the PRD, the ticketing system, and the codebase.
* **Lack of Governance:** Fully autonomous coding agents often break existing repository structures because they lack "Human-in-the-Loop" approval gates for architectural decisions.

**2.3 Problem Statement**
There is currently no standardized, open-source enterprise system that acts as an "AI Engineering OS" to orchestrate the entire SDLC. The manual bridging of product requirements (Confluence), task tracking (Jira), and codebase implementation (GitHub) creates bottlenecks, reduces developer velocity, and increases the likelihood of human error during repetitive setup tasks.

**2.4 Significance of the Study**
This project is significant because it introduces a highly structured, role-based multi-agent system (MAS). By delegating specific tasks to specialized agents (e.g., Architecture Agent vs. QA Agent), the system mirrors a real engineering organization, contributing to the safe and scalable adoption of AI in enterprise software development.

---

### CHAPTER 3: OBJECTIVES & SCOPE

**3.1 Primary Objective**
To design and develop a human-supervised AI Engineering Orchestrator that automates structured SDLC workflows across Confluence, Jira, and GitHub, acting as a collaborative organization that implements code based on approved architecture plans.

**3.2 Specific Objectives**

* **To Construct an Initialization Pipeline:** Develop a collaborative chat interface where a Product Manager Agent translates ideas into Confluence PRDs and structured Jira Epics/Stories.
* **To Engineer an Event-Driven Orchestrator:** Build a FastAPI-based control plane that listens to Jira webhooks to autonomously trigger code generation and local QA testing.
* **To Implement a Self-Correcting QA Loop:** Utilize a local execution environment to run `pytest`, parse failure logs, and feed them back to a Dev Agent for autonomous self-correction (up to a maximum retry limit).

**3.3 Scope of the Project**

* The system utilizes Next.js for the human-facing interface and FastAPI for the backend orchestrator.
* It focuses on backend code generation (Python/FastAPI templates).
* Integrations are strictly bound to GitHub, Atlassian Jira, and Atlassian Confluence via API/SDKs.

**3.4 Limitations**

* The current MVP scope does not handle multi-repository microservices architectures or automated cloud deployment pipelines (e.g., AWS/GCP DevOps agents).
* The AI will only write backend code and tests; frontend UI component generation is out of scope.

---

### CHAPTER 4: METHODOLOGY & SYSTEM ARCHITECTURE

**4.1 Research Methodology**
This project follows the Experimental Development methodology. The software will be built iteratively through distinct phases: establishing the API integrations via the Model Context Protocol (MCP), designing the Orchestrator State Machine, and implementing the multi-agent execution loop.

**4.2 System Architecture Overview** The system adopts an Event-Driven Control Plane architecture:

* **Frontend Interface (Next.js):** Provides a dashboard for human supervisors to brainstorm PRDs and approve architecture plans.
* **Backend Orchestrator (FastAPI):** Acts as the central nervous system. It maintains ticket state, controls retries, and routes execution to the correct specialized agent.
* **Integration Layer:** Abstracted "Skills" execute external actions via APIs (e.g., `create_github_branch`, `run_tests`), preventing agents from making chaotic, uncontrolled API calls directly.

**4.3 Technology Stack Justification** * **FastAPI (Python):** Chosen for its native asynchronous capabilities, which are crucial for listening to webhooks and managing long-running LLM network calls without blocking.

* **Supabase (PostgreSQL):** Selected to enforce strict relational state tracking for Jira tickets and agent execution logs.
* **LangChain / LLM SDKs:** Provides the foundational cognitive logic for reasoning, planning, and formatting outputs for the various specialized agents.

---

### CHAPTER 5: PROPOSED SYSTEM MODULES

**5.1 Module 1: Project Initialization & PRD Generation**
Triggered interactively, a Product Manager (PM) Agent converses with the user to extract non-functional requirements and constraints, formulating a highly structured PRD saved directly to Confluence. Subsequently, an Architecture Agent defines the database schema and technical stack, awaiting human approval before proceeding.

**5.2 Module 2: Repository Bootstrap & Task Structuring**
Once the architecture is approved, the Repo Bootstrap Agent provisions a new GitHub repository, pushing a base FastAPI app and Dockerfile. Simultaneously, the Jira Structuring Agent breaks the PRD down into actionable Epics and Stories, effectively translating product vision into an engineering backlog.

**5.3 Module 3: Event-Driven Orchestrator & State Machine**
The core control plane tracks the lifecycle of every Jira ticket through an internal state machine (e.g., `AI_READY → PLANNING → IN_DEVELOPMENT → IN_QA → READY_TO_MERGE`). It securely dispatches external tools based on the current active state.

**5.4 Module 4: Autonomous Execution Loop**
Triggered by a webhook when a Jira ticket moves to "AI Ready". A Planning Agent analyzes the repository and defines the files to modify. A Dev Agent creates a branch, writes the code, and opens a Pull Request. A QA Agent then executes local tests, parsing any failure logs to trigger an automated fix loop (capped at a maximum of 3 retries).

**5.5 Module 5: Code Review & Traceability**
A Review Agent compares the finalized Pull Request against the original Jira acceptance criteria and architectural constraints. If successful, a Release Agent automatically merges the PR, updates the Jira ticket status to "Done," and appends a release summary comment, closing the operational loop.

---

### CHAPTER 6: FEASIBILITY STUDY

**6.1 Technical Feasibility**
The architecture is highly feasible. Utilizing specialized agents scoped to single responsibilities (e.g., Planning vs. Execution) reduces the LLM hallucination rate significantly. Furthermore, forcing agents to request abstracted "skills" (managed by the FastAPI orchestrator) ensures deterministic, controllable API execution.

**6.2 Operational Feasibility**
The system introduces a strict "human-in-the-loop" governance model for high-stakes decisions (Architecture and Epic creation). Economically, it leverages the free developer tiers of GitHub, Jira, and Confluence, making it a highly cost-effective orchestration engine capable of running on a standard local machine or standard cloud container.

---

### CHAPTER 7: EXPECTED OUTCOMES

Upon successful completion, the project will deliver:

1. **A Functional Orchestrator Application:** A deployed interface managing the initialization of PRDs and automated GitHub repository setups.
2. **Autonomous Ticket Execution Demonstration:** A live, end-to-end demonstration where moving a Jira ticket to "AI Ready" autonomously results in tested, structurally compliant backend code merged into a GitHub Pull Request.
3. **Traceability Metrics:** Comprehensive logs showcasing the reduction in feature implementation cycle time and manual administrative overhead.

---

### CHAPTER 8: PROJECT TIMELINE

* **Weeks 1–2:** Requirement Analysis & Architecture Design (State machine mapping, database schema design).
* **Weeks 3–5:** Phase 1 Implementation (PM Agent, Architecture Agent, Confluence/Jira integration).
* **Weeks 6–8:** Phase 2 Implementation (FastAPI Orchestrator, Dev Agent, QA Agent, GitHub integration).
* **Weeks 9–10:** Next.js Frontend Development & UI Integration.
* **Weeks 11–12:** End-to-End Testing, Bug Fixing, and Final Report Submission.

---

### REFERENCES

1. Atlassian. (2023). *Jira and Confluence REST API Documentation*. Retrieved from developer.atlassian.com
2. GitHub. (2023). *GitHub REST API v3 Documentation*. Retrieved from docs.github.com
3. Talebirad, Y., & Nadiri, A. (2023). *Multi-Agent Collaboration: Harnessing the Power of Intelligent LLM Agents*. arXiv preprint arXiv:2306.03314.
4. Anthropic. (2025). *How we built our multi-agent research system*. Retrieved from [anthropic.com/engineering](https://www.google.com/search?q=https://anthropic.com/engineering)
5. Hong, S., et al. (2023). *MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework*. arXiv preprint arXiv:2308.00352.
6. Zheng, L., et al. (2023). *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*. arXiv preprint arXiv:2306.05685.

