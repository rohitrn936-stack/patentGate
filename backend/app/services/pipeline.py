"""In-process orchestration of the PatentGate multi-agent pipeline.

    product (+ image)
      -> Agent 1  (feature extraction + knowledge analysis)
      -> Patent search layer  (PatentsView / Google Patents / Tavily / stubs)
      -> Agent 2 (Prosecutor)   risky claim-element mappings
      -> Agent 3 (Defender)     distinctions / gaps / weak elements
      -> Agent 4 (Design)       3 design-around alternatives
      -> Risk matrix (deterministic)
      -> Agent 5 (Final report) consolidated report + attorney questions
      -> DALL-E before/after concept images (best-effort, non-blocking)

``stream_analysis_pipeline`` is an async generator that yields
:class:`PipelineEvent` objects as each stage completes, so the SSE endpoint can
push partial results to the UI immediately. Every stage's validated output is
also persisted to ``agent_runs`` (plus a few denormalized rows), so a reload
rehydrates the same result via ``GET /api/analyses/{id}`` and a partial or
failed run stays inspectable.

``run_analysis_pipeline`` simply drains the generator; it is what the legacy
``POST /api/analyses/{id}/run`` background task calls.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import tempfile
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import httpx
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
from app.services import events as E
from app.services.events import PipelineEvent

logger = logging.getLogger("patentgate.pipeline")

MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", Path(__file__).resolve().parents[2] / "media"))


# --------------------------------------------------------------------------- #
# persistence helpers
# --------------------------------------------------------------------------- #
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


async def _set_status(db: AsyncSession, analysis_id: UUID, status: str) -> None:
    analysis = await db.get(Analysis, analysis_id)
    if analysis is not None:
        analysis.status = status
        await db.commit()


# --------------------------------------------------------------------------- #
# blocking agent steps (run via asyncio.to_thread)
# --------------------------------------------------------------------------- #
def _agent1_sync(description: str, image_data_url: str | None) -> dict:
    from agent1 import run_agent1

    if not image_data_url:
        return run_agent1(description, load_env=True).model_dump()

    # run_agent1 only accepts a local image path; write the data URL to a
    # temp file so vision input still flows through the same code path.
    header, _, b64 = image_data_url.partition(",")
    ext = ".png" if "png" in header else ".jpg"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as fh:
        fh.write(base64.b64decode(b64))
        tmp_path = fh.name
    try:
        return run_agent1(description, image_path=tmp_path, load_env=True).model_dump()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _search_sync(agent1_out: dict) -> dict:
    from patent_search import PatentSearchService

    return PatentSearchService().search(agent1_out).model_dump()


def _prosecutor_sync(product: dict, patents: list[dict]) -> dict:
    from agent2 import Prosecutor

    return Prosecutor().analyze(product, patents).model_dump()


def _defender_sync(agent1_out: dict, prosecutor_out: dict, patents: list[dict]) -> dict:
    from agent3.agent import Defender

    analysis = agent1_out.get("analysis", {}) or {}
    defender_input = {
        "invention": analysis.get("invention") or agent1_out.get("product", {}).get("summary", ""),
        "claim_elements": [
            {
                "id": m.get("claim_id", ""),
                "element": m.get("claim_element", ""),
                "patent_id": m.get("patent_id", ""),
            }
            for m in prosecutor_out.get("claim_element_mappings", []) or []
        ],
        "prior_art": patents,
        "prosecutor_risk_claims": prosecutor_out.get("risk_claims", []) or [],
        "prosecutor_confidence": prosecutor_out.get("confidence_per_patent", []) or [],
    }
    return Defender().analyze(defender_input).model_dump()


def _design_sync(product: dict, prosecutor_out: dict, defender_out: dict) -> dict:
    from agent4 import DesignEngineer

    return DesignEngineer().generate(product, prosecutor_out, defender_out).model_dump()


def _risk_matrix(description: str, prosecutor_out: dict, defender_out: dict, design_out: dict) -> dict:
    from risk_matrix import RiskMatrixRequest, RiskMatrixService

    mappings = prosecutor_out.get("claim_element_mappings", []) or []
    all_elements = [m.get("claim_element", "") for m in mappings if m.get("claim_element")]
    strong = {"high", "strong", "moderate", "medium"}
    risky = [
        m["claim_element"]
        for m in mappings
        if m.get("claim_element") and str(m.get("strength", "")).lower() in strong
    ]
    if not risky:
        risky = list(all_elements)

    findings = (
        (prosecutor_out.get("risk_claims", []) or [])
        + (defender_out.get("distinctions", []) or [])
        + (defender_out.get("prior_art_gaps", []) or [])
        + (defender_out.get("weak_claim_elements", []) or [])
    )
    request = RiskMatrixRequest(
        product_description=description or "n/a",
        claim_elements=[e for e in all_elements if e],
        risky_elements=[e for e in risky if e],
        prior_art_findings=findings,
        redesign_options=design_out.get("alternatives", []) or [],
    )
    return RiskMatrixService().generate(request).model_dump()


def _report_sync(
    feature_extraction: dict,
    patents: list[dict],
    prosecutor_out: dict,
    defender_out: dict,
    risk_out: dict,
    design_out: dict,
) -> dict:
    from report_agent import ReportGenerator

    return ReportGenerator().generate(
        feature_extraction=feature_extraction,
        patents=patents,
        prosecutor=prosecutor_out,
        defender=defender_out,
        risk_matrix=risk_out,
        design=design_out,
    ).model_dump()


def _image_config_ready() -> bool:
    from llm.config import resolve_llm_config

    cfg = resolve_llm_config(agent="image")
    return bool(cfg.api_key) or cfg.provider == "local"


def _images_sync(analysis_id: str, agent1_out: dict, risky: list[str], design_out: dict) -> dict:
    from image_genration import DesignOption, ImageGenerationRequest, ImageGenerationService

    alternatives = design_out.get("alternatives", []) or []
    options = [
        DesignOption(
            option_id=int(a.get("id", i + 1)),
            title=(a.get("avoids_claim_element") or f"Option {a.get('id', i + 1)}")[:120],
            description=a.get("description", ""),
            key_changes=a.get("changes_from_original", []) or [],
            prompt_override=a.get("design_generation_prompt"),
        )
        for i, a in enumerate(alternatives)
    ]
    if not options:
        return {"status": "error", "images": [], "error": "no design options"}

    out_dir = MEDIA_ROOT / "analyses" / analysis_id
    service = ImageGenerationService(output_dir=str(out_dir))
    request = ImageGenerationRequest(
        product_description=agent1_out.get("product", {}).get("summary", "") or "product",
        original_concept=agent1_out.get("product", {}).get("summary"),
        risky_elements=risky,
        design_options=options,
    )
    response = service.generate(request)

    images: list[dict] = []
    for img in response.images:
        url = img.image_url
        # Re-host remote (DALL-E) URLs so they survive past their ~1h expiry.
        if url and url.startswith("http"):
            try:
                data = httpx.get(url, timeout=30.0).content
                dest = out_dir / f"option_{img.option_id}.png"
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                url = f"/media/analyses/{analysis_id}/option_{img.option_id}.png"
            except Exception:  # noqa: BLE001 - keep the original URL on failure
                pass
        elif img.image_path:
            rel = Path(img.image_path).name
            url = f"/media/analyses/{analysis_id}/{rel}"
        images.append(
            {
                "option_id": img.option_id,
                "image_url": url,
                "status": img.status,
                "error": img.error,
                "prompt_used": img.prompt_used,
            }
        )
    return {"status": response.status, "images": images, "error": response.error}


# --------------------------------------------------------------------------- #
# the streaming pipeline
# --------------------------------------------------------------------------- #
async def stream_analysis_pipeline(analysis_id: UUID) -> AsyncIterator[PipelineEvent]:
    seq = 0

    def ev(type_: str, *, stage: str | None = None, data=None, message: str | None = None):
        nonlocal seq
        seq += 1
        return PipelineEvent(type=type_, stage=stage, data=data, message=message, seq=seq)

    async with AsyncSessionLocal() as db:
        analysis = await db.get(Analysis, analysis_id)
        if analysis is None:
            yield ev(E.ERROR, message="analysis not found")
            return
        product = await db.get(Product, analysis.product_id)
        if product is None:
            await _set_status(db, analysis_id, "failed")
            yield ev(E.ERROR, message="product not found")
            return

        description = product.description or ""
        stage = "feature_extraction"
        completed = False
        try:
            yield ev(E.USER_INPUT, stage=stage, data={"product": product.name})

            # -- Agent 1 -------------------------------------------------
            await _set_status(db, analysis_id, "feature_extraction")
            yield ev(E.FEATURE_EXTRACTION_STARTED, stage=stage)
            agent1_out = await asyncio.to_thread(_agent1_sync, description, product.image_url)
            await _record_run(db, analysis_id, "feature_extractor", status="completed", output_data=agent1_out)
            for f in agent1_out.get("features", []) or []:
                db.add(
                    ProductFeature(
                        analysis_id=analysis_id,
                        feature_name=(f.get("name") or "feature")[:255],
                        description=f.get("description"),
                        importance=f.get("confidence"),
                    )
                )
            await db.commit()
            yield ev(E.FEATURE_EXTRACTION_COMPLETED, stage=stage, data=agent1_out)

            # -- Patent search ----------------------------------------
            stage = "patent_search"
            await _set_status(db, analysis_id, "patent_search")
            yield ev(E.PATENT_SEARCH_STARTED, stage=stage)
            search_out = await asyncio.to_thread(_search_sync, agent1_out)
            patents = search_out.get("patents", []) or []
            for p in patents:
                db.add(
                    Patent(
                        analysis_id=analysis_id,
                        title=p.get("title"),
                        patent_number=p.get("patent_number"),
                        abstract=p.get("abstract"),
                        source=p.get("source"),
                        source_url=p.get("source_url"),
                        relevance_score=p.get("relevance_score"),
                    )
                )
                yield ev(E.PATENT_FOUND, stage=stage, data=p)
            await db.commit()
            await _record_run(db, analysis_id, "patent_search", status="completed", output_data=search_out)
            yield ev(
                E.PATENT_SEARCH_COMPLETED,
                stage=stage,
                data={
                    "queries": search_out.get("queries", []),
                    "sources_used": search_out.get("sources_used", []),
                    "warnings": search_out.get("warnings", []),
                    "count": len(patents),
                },
            )
            for w in search_out.get("warnings", []) or []:
                yield ev(E.WARNING, stage=stage, message=w)

            product_payload = {
                "name": agent1_out.get("product", {}).get("name") or product.name,
                "description": description,
                "features": [f.get("name", "") for f in agent1_out.get("features", []) or []],
            }
            agent_patents = [
                {
                    "id": p.get("patent_number") or p.get("title") or "UNKNOWN",
                    "summary": p.get("abstract") or p.get("title") or "",
                    "claims": p.get("claims") or f"{p.get('title', '')}. {p.get('abstract', '')}".strip(". "),
                }
                for p in patents
            ] or [{"id": "NONE", "summary": "No prior art retrieved.", "claims": ""}]

            # -- Agent 2 (Prosecutor) --------------------------------
            stage = "analysis"
            await _set_status(db, analysis_id, "analysis")
            yield ev(E.PROSECUTOR_STARTED, stage="prosecutor")
            prosecutor_out = await asyncio.to_thread(_prosecutor_sync, product_payload, agent_patents)
            await _record_run(db, analysis_id, "prosecutor", status="completed", output_data=prosecutor_out)
            yield ev(E.PROSECUTOR_COMPLETED, stage="prosecutor", data=prosecutor_out)

            # -- Agent 3 (Defender) ---------------------------------
            yield ev(E.DEFENDER_STARTED, stage="defender")
            defender_out = await asyncio.to_thread(
                _defender_sync, agent1_out, prosecutor_out, agent_patents
            )
            await _record_run(db, analysis_id, "defender", status="completed", output_data=defender_out)
            yield ev(E.DEFENDER_COMPLETED, stage="defender", data=defender_out)

            # -- Agent 4 (Design engineer) --------------------------
            stage = "design_generation"
            await _set_status(db, analysis_id, "design_generation")
            yield ev(E.DESIGN_ENGINEER_STARTED, stage=stage)
            design_out = await asyncio.to_thread(
                _design_sync, product_payload, prosecutor_out, defender_out
            )
            for alt in design_out.get("alternatives", []) or []:
                db.add(
                    DesignAlternative(
                        analysis_id=analysis_id,
                        title=(alt.get("avoids_claim_element") or f"Alternative {alt.get('id')}")[:80],
                        description=alt.get("description"),
                        changed_feature=", ".join(alt.get("changes_from_original", []) or []) or None,
                        preserved_function=alt.get("why_it_differs"),
                        tradeoffs=alt.get("tradeoff"),
                    )
                )
            await db.commit()
            yield ev(E.DESIGN_OPTIONS_GENERATED, stage=stage, data=design_out)

            # -- Risk matrix (deterministic) ------------------------
            risk_out = _risk_matrix(description, prosecutor_out, defender_out, design_out)
            db.add(
                RiskScore(
                    analysis_id=analysis_id,
                    overall_score=risk_out.get("overall_score"),
                    risk_level=(str(risk_out.get("overall_risk") or "").lower() or None),
                    explanation="; ".join(
                        r.get("reason", "") for r in risk_out.get("risks", []) or []
                    )
                    or None,
                )
            )
            await db.commit()
            await _record_run(
                db,
                analysis_id,
                "design_engineer",
                status="completed",
                output_data={**design_out, "risk_matrix": risk_out},
            )
            yield ev(E.RISK_MATRIX_READY, stage=stage, data=risk_out)

            # -- Agent 5 (Final report) - does not wait on images --
            stage = "report"
            report_out = await asyncio.to_thread(
                _report_sync, agent1_out, patents, prosecutor_out, defender_out, risk_out, design_out
            )
            yield ev(E.FINAL_REPORT_READY, stage=stage, data=report_out)

            # -- DALL-E concept images (best-effort, non-blocking) --
            stage = "image_generation"
            images_payload: dict = {"status": "skipped", "images": []}
            if not _image_config_ready():
                yield ev(
                    E.IMAGE_GENERATION_SKIPPED,
                    stage=stage,
                    message="No image provider configured (set IMAGE_LLM_API_KEY / OPENAI_API_KEY).",
                )
            else:
                yield ev(E.IMAGE_GENERATION_STARTED, stage=stage)
                risky_elements = [
                    r.get("claim_element", "")
                    for r in risk_out.get("risks", []) or []
                    if str(r.get("risk_level", "")).lower() in {"high", "medium"}
                ]
                try:
                    images_payload = await asyncio.to_thread(
                        _images_sync, str(analysis_id), agent1_out, risky_elements, design_out
                    )
                    for img in images_payload.get("images", []) or []:
                        if img.get("image_url"):
                            alt_id = img.get("option_id")
                            rows = (
                                await db.execute(
                                    select(DesignAlternative).where(
                                        DesignAlternative.analysis_id == analysis_id
                                    )
                                )
                            ).scalars().all()
                            if 0 < (alt_id or 0) <= len(rows):
                                rows[alt_id - 1].image_url = img["image_url"]
                        yield ev(E.REDESIGN_IMAGE_READY, stage=stage, data=img)
                    await db.commit()
                except Exception as exc:  # noqa: BLE001 - images never fail the run
                    logger.warning("image generation failed: %s", exc)
                    yield ev(E.IMAGE_GENERATION_SKIPPED, stage=stage, message=f"image generation failed: {exc}")

            report_out["redesign_concepts"] = images_payload.get("images", []) or []
            await _record_run(db, analysis_id, "report", status="completed", output_data=report_out)

            fresh = await db.get(Analysis, analysis_id)
            fresh.status = "completed"
            fresh.completed_at = datetime.now(UTC)
            await db.commit()
            completed = True
            yield ev(E.PIPELINE_COMPLETED, stage="completed", data={"analysis_id": str(analysis_id)})
            logger.info("pipeline: analysis %s completed", analysis_id)

        except Exception as exc:  # noqa: BLE001 - recorded, surfaced, not re-raised
            await db.rollback()
            fresh = await db.get(Analysis, analysis_id)
            if fresh is not None:
                fresh.status = "failed"
                await db.commit()
            await _record_run(
                db, analysis_id, stage, status="failed", error_message=f"{stage}: {exc}"[:2000]
            )
            logger.exception("pipeline: analysis %s failed at %s", analysis_id, stage)
            yield ev(E.ERROR, stage=stage, message=f"{stage}: {exc}")
        finally:
            if not completed:
                cur = await db.get(Analysis, analysis_id)
                if cur is not None and cur.status not in {"completed", "failed"}:
                    cur.status = "failed"
                    await db.commit()


async def run_analysis_pipeline(analysis_id: UUID) -> None:
    """Drain the streaming pipeline (used by ``POST /api/analyses/{id}/run``)."""

    async for _ in stream_analysis_pipeline(analysis_id):
        pass


# --------------------------------------------------------------------------- #
# result assembly for GET /api/analyses/{id}
# --------------------------------------------------------------------------- #
async def load_analysis_result(db: AsyncSession, analysis_id: UUID) -> dict:
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
    design = completed.get("design_engineer")
    search = completed.get("patent_search") or {}
    report = completed.get("report") or {}

    return {
        "feature_extraction": completed.get("feature_extractor"),
        "patent_search": search or None,
        "patents": search.get("patents", []) if search else [],
        "prosecutor": completed.get("prosecutor"),
        "defender": completed.get("defender"),
        "design": design,
        "risk_matrix": (design or {}).get("risk_matrix"),
        "report": report or None,
        "images": report.get("redesign_concepts", []) if report else [],
        "errors": [
            {"stage": r.agent_type, "message": r.error_message}
            for r in runs
            if r.status == "failed" and r.error_message
        ],
    }


__all__ = ["stream_analysis_pipeline", "run_analysis_pipeline", "load_analysis_result", "MEDIA_ROOT"]
