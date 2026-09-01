from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models import Analysis, Product, User
from app.rate_limit import ANALYSIS_RUN_LIMIT
from app.schemas.analysis import AnalysisCreate, AnalysisDetail, AnalysisRead
from app.services.pipeline import load_analysis_result, run_analysis_pipeline

router = APIRouter(prefix="/api/analyses", tags=["analyses"])

# Statuses from which a (re)run may be started.
_RUNNABLE = {"pending", "failed", "completed"}


async def _owned_analysis(analysis_id: UUID, user: User, db: AsyncSession) -> Analysis:
    result = await db.execute(
        select(Analysis)
        .join(Product, Analysis.product_id == Product.id)
        .where(Analysis.id == analysis_id, Product.user_id == user.id)
    )
    analysis = result.scalar_one_or_none()
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return analysis


@router.post("", response_model=AnalysisRead, status_code=status.HTTP_201_CREATED)
async def create_analysis(
    payload: AnalysisCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Analysis:
    product = (
        await db.execute(
            select(Product).where(
                Product.id == payload.product_id, Product.user_id == current_user.id
            )
        )
    ).scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    analysis = Analysis(product_id=product.id, status="pending")
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    return analysis


@router.get("", response_model=list[AnalysisRead])
async def list_analyses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Analysis]:
    result = await db.execute(
        select(Analysis)
        .join(Product, Analysis.product_id == Product.id)
        .where(Product.user_id == current_user.id)
        .order_by(Analysis.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{analysis_id}", response_model=AnalysisDetail)
async def get_analysis(
    analysis_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalysisDetail:
    analysis = await _owned_analysis(analysis_id, current_user, db)
    result = await load_analysis_result(db, analysis_id)
    return AnalysisDetail(
        **AnalysisRead.model_validate(analysis).model_dump(),
        **result,
    )


@router.post(
    "/{analysis_id}/run",
    response_model=AnalysisRead,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[ANALYSIS_RUN_LIMIT],
)
async def run_analysis(
    analysis_id: UUID,
    background: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Analysis:
    analysis = await _owned_analysis(analysis_id, current_user, db)
    if analysis.status not in _RUNNABLE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Analysis is already running (status: {analysis.status})",
        )

    analysis.status = "pending"
    analysis.completed_at = None
    await db.commit()
    await db.refresh(analysis)

    background.add_task(run_analysis_pipeline, analysis.id)
    return analysis
