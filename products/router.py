from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from core.database import get_db
from auth.dependencies import get_current_user
from auth.models import User
from products import crud, schemas

router = APIRouter(prefix="/products", tags=["products"])

@router.get("/", response_model=List[schemas.ProductResponse])
async def get_products(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await crud.get_products(db, current_user.id)

@router.get("/{product_id}", response_model=schemas.ProductResponse)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = await crud.get_product_by_id(db, product_id, current_user.id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {product_id} not found")
    return product

@router.post("/", response_model=schemas.ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(product_in: schemas.ProductCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await crud.create_product(db, product_in, current_user.id)

@router.put("/{product_id}", response_model=schemas.ProductResponse)
async def update_product(product_id: int, product_in: schemas.ProductUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = await crud.update_product(db, product_id, product_in, current_user.id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {product_id} not found")
    return product

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not await crud.delete_product(db, product_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {product_id} not found")
