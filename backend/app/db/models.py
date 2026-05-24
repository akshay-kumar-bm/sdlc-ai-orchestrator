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
    ticket_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ticket_executions.id"), nullable=True
    )
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
    approval_type: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
