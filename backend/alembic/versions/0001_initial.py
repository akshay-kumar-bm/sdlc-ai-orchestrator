"""initial

Revision ID: 0001
Revises:
Create Date: 2026-05-24
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="INITIALIZED"),
        sa.Column("confluence_prd_url", sa.Text, nullable=True),
        sa.Column("confluence_arch_url", sa.Text, nullable=True),
        sa.Column("github_repo_url", sa.Text, nullable=True),
        sa.Column("jira_project_key", sa.String(50), nullable=True),
        sa.Column("confluence_space_key", sa.String(50), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "ticket_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False
        ),
        sa.Column("jira_ticket_key", sa.String(50), nullable=False),
        sa.Column("github_issue_url", sa.Text, nullable=True),
        sa.Column("github_pr_url", sa.Text, nullable=True),
        sa.Column("github_branch", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="AI_READY"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("current_agent", sa.String(100), nullable=True),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "agent_execution_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ticket_execution_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ticket_executions.id"), nullable=True),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True
        ),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("skill_requested", sa.String(100), nullable=True),
        sa.Column("input_payload", postgresql.JSONB, nullable=True),
        sa.Column("output_payload", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("token_usage", sa.Integer, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "human_approval_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False
        ),
        sa.Column("approval_type", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="PENDING"),
        sa.Column("feedback", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    op.create_index("idx_ticket_executions_status", "ticket_executions", ["status"])
    op.create_index("idx_ticket_executions_project", "ticket_executions", ["project_id"])
    op.create_index("idx_agent_logs_ticket", "agent_execution_logs", ["ticket_execution_id"])


def downgrade() -> None:
    op.drop_index("idx_agent_logs_ticket")
    op.drop_index("idx_ticket_executions_project")
    op.drop_index("idx_ticket_executions_status")
    op.drop_table("human_approval_requests")
    op.drop_table("agent_execution_logs")
    op.drop_table("ticket_executions")
    op.drop_table("projects")
