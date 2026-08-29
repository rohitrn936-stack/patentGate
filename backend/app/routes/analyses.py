from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models import Analysis, Product, User
from app.schemas.analysis import AnalysisCreate, AnalysisRead


router = APIRouter(prefix="/api/analyses", tags=["analyses"])


@router.post("", response_model=AnalysisRead, status_code=status.HTTP_201_CREATED)
async def create_analysis(
    payload: AnalysisCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Analysis:
    product_result = await db.execute(
        select(Product).where(Product.id == payload.product_id, Product.user_id == current_user.id)
    )
    product = product_result.scalar_one_or_none()
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
        .join(Product)
        .where(Product.user_id == current_user.id)
        .order_by(Analysis.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{analysis_id}", response_model=AnalysisRead)
async def get_analysis(
    analysis_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Analysis:
    result = await db.execute(
        select(Analysis).join(Product).where(Analysis.id == analysis_id, Product.user_id == current_user.id)
    )
    analysis = result.scalar_one_or_none()
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return analysis
