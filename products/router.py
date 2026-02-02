from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from core.database import get_db
from auth.dependencies import get_current_user
from auth.models import User
from products.service import ProductService
from products import schemas

router = APIRouter(prefix="/products", tags=["products"])


def get_product_service(db: AsyncSession = Depends(get_db)) -> ProductService:
    """Dependency to get ProductService instance."""
    return ProductService(db)


@router.get("/", response_model=List[schemas.ProductResponse])
async def get_products(
    service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_user)
):
    return await service.get_all(current_user.id)


@router.get("/{product_id}", response_model=schemas.ProductResponse)
async def get_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_user)
):
    product = await service.get_by_id(product_id, current_user.id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )
    return product


@router.post("/", response_model=schemas.ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_in: schemas.ProductCreate,
    service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_user)
):
    return await service.create(product_in, current_user.id)


@router.put("/{product_id}", response_model=schemas.ProductResponse)
async def update_product(
    product_id: int,
    product_in: schemas.ProductUpdate,
    service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_user)
):
    product = await service.update(product_id, product_in, current_user.id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_user)
):
    if not await service.delete(product_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product {product_id} not found"
        )
