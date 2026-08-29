"""initial schema

Revision ID: 202608300001
Revises:
Create Date: 2026-08-30 00:01:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "202608300001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_products_user_id"), "products", ["user_id"], unique=False)

    op.create_table(
        "analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'feature_extraction', 'patent_search', 'analysis', 'design_generation', 'completed', 'failed')",
            name="ck_analyses_status",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analyses_product_id"), "analyses", ["product_id"], unique=False)

    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_type", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("input_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("output_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "agent_type IN ('feature_extractor', 'prosecutor', 'defender', 'design_engineer')",
            name="ck_agent_runs_agent_type",
        ),
        sa.CheckConstraint("status IN ('pending', 'running', 'completed', 'failed')", name="ck_agent_runs_status"),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_runs_analysis_id"), "agent_runs", ["analysis_id"], unique=False)

    op.create_table(
        "design_alternatives",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("changed_feature", sa.Text(), nullable=True),
        sa.Column("preserved_function", sa.Text(), nullable=True),
        sa.Column("tradeoffs", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_design_alternatives_analysis_id"), "design_alternatives", ["analysis_id"], unique=False)

    op.create_table(
        "patents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("patent_number", sa.String(), nullable=True),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("published_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_patents_analysis_id"), "patents", ["analysis_id"], unique=False)
    op.create_index(op.f("ix_patents_patent_number"), "patents", ["patent_number"], unique=False)

    op.create_table(
        "product_features",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feature_name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("importance", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_product_features_analysis_id"), "product_features", ["analysis_id"], unique=False)

    op.create_table(
        "risk_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("risk_level", sa.String(), nullable=True),
        sa.Column("prosecutor_score", sa.Float(), nullable=True),
        sa.Column("defender_score", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_risk_scores_analysis_id"), "risk_scores", ["analysis_id"], unique=False)

    op.create_table(
        "patent_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_number", sa.Integer(), nullable=True),
        sa.Column("claim_text", sa.Text(), nullable=True),
        sa.Column("is_independent", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["patent_id"], ["patents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_patent_claims_patent_id"), "patent_claims", ["patent_id"], unique=False)

    op.create_table(
        "patent_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("risk_level", sa.String(), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patent_id"], ["patents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_patent_analyses_analysis_id"), "patent_analyses", ["analysis_id"], unique=False)
    op.create_index(op.f("ix_patent_analyses_patent_id"), "patent_analyses", ["patent_id"], unique=False)

    op.create_table(
        "defender_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patent_analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("argument", sa.Text(), nullable=True),
        sa.Column("distinction_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["patent_claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patent_analysis_id"], ["patent_analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_defender_results_claim_id"), "defender_results", ["claim_id"], unique=False)
    op.create_index(op.f("ix_defender_results_patent_analysis_id"), "defender_results", ["patent_analysis_id"], unique=False)

    op.create_table(
        "prosecutor_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patent_analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("argument", sa.Text(), nullable=True),
        sa.Column("overlap_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["patent_claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patent_analysis_id"], ["patent_analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_prosecutor_results_claim_id"), "prosecutor_results", ["claim_id"], unique=False)
    op.create_index(op.f("ix_prosecutor_results_patent_analysis_id"), "prosecutor_results", ["patent_analysis_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_prosecutor_results_patent_analysis_id"), table_name="prosecutor_results")
    op.drop_index(op.f("ix_prosecutor_results_claim_id"), table_name="prosecutor_results")
    op.drop_table("prosecutor_results")
    op.drop_index(op.f("ix_defender_results_patent_analysis_id"), table_name="defender_results")
    op.drop_index(op.f("ix_defender_results_claim_id"), table_name="defender_results")
    op.drop_table("defender_results")
    op.drop_index(op.f("ix_patent_analyses_patent_id"), table_name="patent_analyses")
    op.drop_index(op.f("ix_patent_analyses_analysis_id"), table_name="patent_analyses")
    op.drop_table("patent_analyses")
    op.drop_index(op.f("ix_patent_claims_patent_id"), table_name="patent_claims")
    op.drop_table("patent_claims")
    op.drop_index(op.f("ix_risk_scores_analysis_id"), table_name="risk_scores")
    op.drop_table("risk_scores")
    op.drop_index(op.f("ix_product_features_analysis_id"), table_name="product_features")
    op.drop_table("product_features")
    op.drop_index(op.f("ix_patents_patent_number"), table_name="patents")
    op.drop_index(op.f("ix_patents_analysis_id"), table_name="patents")
    op.drop_table("patents")
    op.drop_index(op.f("ix_design_alternatives_analysis_id"), table_name="design_alternatives")
    op.drop_table("design_alternatives")
    op.drop_index(op.f("ix_agent_runs_analysis_id"), table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_index(op.f("ix_analyses_product_id"), table_name="analyses")
    op.drop_table("analyses")
    op.drop_index(op.f("ix_products_user_id"), table_name="products")
    op.drop_table("products")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
