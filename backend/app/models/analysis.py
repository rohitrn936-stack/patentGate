import uuid

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


ANALYSIS_STATUSES = (
    "pending",
    "feature_extraction",
    "patent_search",
    "analysis",
    "design_generation",
    "completed",
    "failed",
)


class Analysis(Base):
    __tablename__ = "analyses"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'feature_extraction', 'patent_search', 'analysis', 'design_generation', 'completed', 'failed')",
            name="ck_analyses_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = mapped_column(DateTime(timezone=True), nullable=True)

    product = relationship("Product", back_populates="analyses")
    product_features = relationship("ProductFeature", back_populates="analysis", cascade="all, delete-orphan")
    patents = relationship("Patent", back_populates="analysis", cascade="all, delete-orphan")
    patent_analyses = relationship("PatentAnalysis", back_populates="analysis", cascade="all, delete-orphan")
    design_alternatives = relationship("DesignAlternative", back_populates="analysis", cascade="all, delete-orphan")
    risk_scores = relationship("RiskScore", back_populates="analysis", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="analysis", cascade="all, delete-orphan")
