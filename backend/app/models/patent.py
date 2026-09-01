import uuid
from datetime import date

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.types import GUID


class ProductFeature(Base):
    __tablename__ = "product_features"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    importance: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    analysis = relationship("Analysis", back_populates="product_features")


class Patent(Base):
    __tablename__ = "patents"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    patent_number: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    published_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    analysis = relationship("Analysis", back_populates="patents")
    claims = relationship("PatentClaim", back_populates="patent", cascade="all, delete-orphan")
    patent_analyses = relationship("PatentAnalysis", back_populates="patent", cascade="all, delete-orphan")


class PatentClaim(Base):
    __tablename__ = "patent_claims"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    patent_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("patents.id", ondelete="CASCADE"), nullable=False, index=True)
    claim_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    claim_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_independent: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    patent = relationship("Patent", back_populates="claims")
    prosecutor_results = relationship("ProsecutorResult", back_populates="claim")
    defender_results = relationship("DefenderResult", back_populates="claim")


class PatentAnalysis(Base):
    __tablename__ = "patent_analyses"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    patent_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("patents.id", ondelete="CASCADE"), nullable=False, index=True)
    risk_level: Mapped[str | None] = mapped_column(String, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    analysis = relationship("Analysis", back_populates="patent_analyses")
    patent = relationship("Patent", back_populates="patent_analyses")
    prosecutor_results = relationship("ProsecutorResult", back_populates="patent_analysis", cascade="all, delete-orphan")
    defender_results = relationship("DefenderResult", back_populates="patent_analysis", cascade="all, delete-orphan")


class ProsecutorResult(Base):
    __tablename__ = "prosecutor_results"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    patent_analysis_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("patent_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("patent_claims.id", ondelete="CASCADE"), nullable=False, index=True)
    argument: Mapped[str | None] = mapped_column(Text, nullable=True)
    overlap_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    patent_analysis = relationship("PatentAnalysis", back_populates="prosecutor_results")
    claim = relationship("PatentClaim", back_populates="prosecutor_results")


class DefenderResult(Base):
    __tablename__ = "defender_results"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    patent_analysis_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("patent_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("patent_claims.id", ondelete="CASCADE"), nullable=False, index=True)
    argument: Mapped[str | None] = mapped_column(Text, nullable=True)
    distinction_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    patent_analysis = relationship("PatentAnalysis", back_populates="defender_results")
    claim = relationship("PatentClaim", back_populates="defender_results")


class DesignAlternative(Base):
    __tablename__ = "design_alternatives"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_feature: Mapped[str | None] = mapped_column(Text, nullable=True)
    preserved_function: Mapped[str | None] = mapped_column(Text, nullable=True)
    tradeoffs: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    analysis = relationship("Analysis", back_populates="design_alternatives")


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String, nullable=True)
    prosecutor_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    defender_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    analysis = relationship("Analysis", back_populates="risk_scores")
