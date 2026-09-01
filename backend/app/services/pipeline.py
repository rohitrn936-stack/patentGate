"""In-process orchestration of the four-agent PatentGate pipeline.

    product (+ image)                       Agent 1  -> features + known concepts
      -> known concepts become pseudo prior-art
      -> Agent 2 (Prosecutor)  -> risky claim-element mappings
      -> Agent 3 (Defender)    -> distinctions / gaps / weak elements
      -> Agent 4 (Design)      -> 3 design-around alternatives
      -> Risk matrix (deterministic)

Every agent runs through the provider-agnostic :mod:`llm` layer. Each step is
persisted to ``agent_runs`` (full validated JSON) plus a few denormalized
convenience tables, so the API can return a rich result and a partial run is
still inspectable.

The blocking agent work runs off the event loop (``asyncio.to_thread``) from a
FastAPI background task with its own database session.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import (
    AgentRun,
    Analysis,
    DesignAlternative,
    Patent,
    Product,
    ProductFeature,
    RiskScore,
)

logger = logging.getLogger("patentgate.pipeline")

_AGENT_SEQUENCE = ("feature_extractor", "prosecutor", "defender", "design_engineer")


async def _record_run(
    db: AsyncSession,
    analysis_id: UUID,
    agent_type: str,
    *,
    status: str,
    output_data: dict | None = None,
    error_message: str | None = None,
) -> None:
    db.add(
        AgentRun(
            analysis_id=analysis_id,
            agent_type=agent_type,
            status=status,
            output_data=output_data,
            error_message=error_message,
            completed_at=datetime.now(UTC),
        )
    )
    await db.commit()


def _concepts_to_pseudo_patents(analysis: dict) -> list[dict]:
    """Agent 1 has no patent DB; turn its known concepts into prior-art stubs."""

    patents: list[dict] = []
    for i, concept in enumerate(analysis.get("similar_known_concepts", []) or [], start=1):
        patents.append(
            {
                "id": f"CONCEPT-{i}",
                "summary": concept.get("why_similar") or concept.get("name", ""),
                "claims": (
                    f"Known concept: {concept.get('name', '')}. "
                    f"Overlapping features: {', '.join(concept.get('matching_features', []))}. "
                    f"Reported differences: {concept.get('differences', '')}"
                ),
            }
        )
    if not patents:
        patents.append(
            {
                "id": "CONCEPT-0",
                "summary": analysis.get("similarity_explanation", "General domain prior art"),
                "claims": "No specific overlapping concepts were identified.",
            }
        )
    return patents


def _run_pipeline_sync(description: str, product_name: str) -> dict:
    """Blocking: run all four agents + the risk matrix."""

    from agent1 import run_agent1
    from agent2 import Prosecutor
    from agent3.agent import Defender
    from agent4 import DesignEngineer
    from risk_matrix import RiskMatrixRequest, RiskMatrixService

    agent1_out = run_agent1(description, load_env=True).model_dump()

    product_payload = {
        "name": agent1_out.get("product", {}).get("name") or product_name,
        "description": description,
        "features": [f["name"] for f in agent1_out.get("features", [])],
    }
    pseudo_patents = _concepts_to_pseudo_patents(agent1_out.get("analysis", {}))

    prosecutor_out = Prosecutor().analyze(product_payload, pseudo_patents).model_dump()

    defender_input = {
        "invention": agent1_out.get("analysis", {}).get("invention", description),
        "claim_elements": [
            {"id": m.get("claim_id", ""), "element": m.get("claim_element", "")}
            for m in prosecutor_out.get("claim_element_mappings", [])
        ],
        "prior_art": pseudo_patents,
        "risk_claims": prosecutor_out.get("risk_claims", []),
    }
    defender_out = Defender().analyze(defender_input).model_dump()

    design_out = (
        DesignEngineer().generate(product_payload, prosecutor_out, defender_out).model_dump()
    )

    risky = [c.get("claim_element", "") for c in defender_out.get("weak_claim_elements", [])]
    claim_elements = [
        m.get("claim_element", "") for m in prosecutor_out.get("claim_element_mappings", [])
    ]
    risk_out = (
        RiskMatrixService()
        .generate(
            RiskMatrixRequest(
                product_description=description,
                claim_elements=[c for c in claim_elements if c],
                risky_elements=[c for c in risky if c],
                prior_art_findings=(
                    prosecutor_out.get("risk_claims", [])
                    + defender_out.get("distinctions", [])
                    + defender_out.get("prior_art_gaps", [])
                ),
                redesign_options=design_out.get("alternatives", []),
            )
        )
        .model_dump()
    )

    return {
        "agent1": agent1_out,
        "agent2": prosecutor_out,
        "agent3": defender_out,
        "agent4": design_out,
        "risk_matrix": risk_out,
    }


async def _persist_denormalized(db: AsyncSession, analysis_id: UUID, result: dict) -> None:
    for feature in result["agent1"].get("features", []):
        db.add(
            ProductFeature(
                analysis_id=analysis_id,
                feature_name=(feature.get("name") or "feature")[:255],
                description=feature.get("description"),
                importance=feature.get("confidence"),
            )
        )
    for concept in result["agent1"].get("analysis", {}).get("similar_known_concepts", []):
        db.add(
            Patent(
                analysis_id=analysis_id,
                title=concept.get("name"),
                abstract=concept.get("why_similar"),
                source="knowledge_analysis",
                relevance_score=concept.get("similarity_score"),
            )
        )
    for alt in result["agent4"].get("alternatives", []):
        db.add(
            DesignAlternative(
                analysis_id=analysis_id,
                title=(alt.get("description") or f"Alternative {alt.get('id')}")[:80],
                description=alt.get("description"),
                changed_feature=alt.get("avoids_claim_element"),
                preserved_function=alt.get("why_it_differs"),
                tradeoffs=alt.get("tradeoff"),
            )
        )
    rm = result["risk_matrix"]
    db.add(
        RiskScore(
            analysis_id=analysis_id,
            overall_score=rm.get("overall_score"),
            risk_level=(str(rm.get("overall_risk") or "").lower() or None),
            explanation=("; ".join(r.get("reason", "") for r in rm.get("risks", [])) or None),
        )
    )
    await db.commit()


async def run_analysis_pipeline(analysis_id: UUID) -> None:
    """Entry point for the FastAPI background task."""

    async with AsyncSessionLocal() as db:
        analysis = await db.get(Analysis, analysis_id)
        if analysis is None:
            logger.warning("pipeline: analysis %s not found", analysis_id)
            return
        product = await db.get(Product, analysis.product_id)
        if product is None:
            analysis.status = "failed"
            await db.commit()
            return

        try:
            analysis.status = "feature_extraction"
            await db.commit()

            result = await asyncio.to_thread(
                _run_pipeline_sync, product.description, product.name
            )

            for agent_type, key in zip(
                _AGENT_SEQUENCE, ("agent1", "agent2", "agent3", "agent4"), strict=True
            ):
                payload = result[key]
                if agent_type == "design_engineer":
                    payload = {**payload, "risk_matrix": result["risk_matrix"]}
                await _record_run(db, analysis_id, agent_type, status="completed", output_data=payload)

            await _persist_denormalized(db, analysis_id, result)

            fresh = await db.get(Analysis, analysis_id)
            fresh.status = "completed"
            fresh.completed_at = datetime.now(UTC)
            await db.commit()
            logger.info("pipeline: analysis %s completed", analysis_id)
        except Exception as exc:  # noqa: BLE001 - recorded on the row, not raised
            await db.rollback()
            fresh = await db.get(Analysis, analysis_id)
            if fresh is not None:
                fresh.status = "failed"
                await db.commit()
            stage = getattr(exc, "stage", type(exc).__name__)
            await _record_run(
                db, analysis_id, "feature_extractor", status="failed",
                error_message=f"{stage}: {exc}"[:2000],
            )
            logger.exception("pipeline: analysis %s failed", analysis_id)


async def load_analysis_result(db: AsyncSession, analysis_id: UUID) -> dict:
    """Assemble the nested result payload for the API from persisted runs."""

    runs = (
        (
            await db.execute(
                select(AgentRun)
                .where(AgentRun.analysis_id == analysis_id)
                .order_by(AgentRun.started_at)
            )
        )
        .scalars()
        .all()
    )
    completed = {r.agent_type: r.output_data for r in runs if r.status == "completed"}
    return {
        "feature_extraction": completed.get("feature_extractor"),
        "prosecutor": completed.get("prosecutor"),
        "defender": completed.get("defender"),
        "design": completed.get("design_engineer"),
        "errors": [
            {"stage": r.agent_type, "message": r.error_message}
            for r in runs
            if r.status == "failed" and r.error_message
        ],
    }
