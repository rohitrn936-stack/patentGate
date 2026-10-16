"""drop the agent_runs.agent_type CHECK constraint

The pipeline gained stages beyond the original four agents (patent_search,
report, image_generation), so the fixed enum on ``agent_runs.agent_type`` no
longer holds. The column stays a plain string.

Revision ID: 202609010002
Revises: 202609010001
Create Date: 2026-09-01 00:02:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "202609010002"
down_revision: str | Sequence[str] | None = "202609010001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("agent_runs") as batch:
            try:
                batch.drop_constraint("ck_agent_runs_agent_type", type_="check")
            except Exception:
                pass
    else:
        op.drop_constraint("ck_agent_runs_agent_type", "agent_runs", type_="check")


def downgrade() -> None:
    op.create_check_constraint(
        "ck_agent_runs_agent_type",
        "agent_runs",
        "agent_type IN ('feature_extractor', 'prosecutor', 'defender', 'design_engineer')",
    )
