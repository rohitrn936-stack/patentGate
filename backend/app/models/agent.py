import uuid

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.types import GUID, JSONBType


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint(
            "agent_type IN ('feature_extractor', 'prosecutor', 'defender', 'design_engineer')",
            name="ck_agent_runs_agent_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_agent_runs_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_type: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True)
    input_data: Mapped[dict | None] = mapped_column(JSONBType(), nullable=True)
    output_data: Mapped[dict | None] = mapped_column(JSONBType(), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = mapped_column(DateTime(timezone=True), nullable=True)

    analysis = relationship("Analysis", back_populates="agent_runs")
