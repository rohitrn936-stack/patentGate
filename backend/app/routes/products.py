from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models import Product, User
from app.schemas.product import ProductCreate, ProductRead


router = APIRouter(prefix="/api/products", tags=["products"])


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Product:
    product = Product(
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        image_url=payload.image_url,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.get("", response_model=list[ProductRead])
async def list_products(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Product]:
    result = await db.execute(
        select(Product).where(Product.user_id == current_user.id).order_by(Product.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Product:
    result = await db.execute(select(Product).where(Product.id == product_id, Product.user_id == current_user.id))
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product
