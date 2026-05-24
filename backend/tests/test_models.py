import app.db.models  # noqa: F401
from app.db.base import Base


def test_all_tables_registered():
    names = set(Base.metadata.tables)
    assert names == {"projects", "ticket_executions", "agent_execution_logs", "human_approval_requests"}
