from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from core.database import get_db
from auth.dependencies import get_current_user
from auth.models import User
from customers import crud, schemas

router = APIRouter(prefix="/customers", tags=["customers"])

@router.get("/", response_model=List[schemas.CustomerResponse])
async def get_customers(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await crud.get_customers(db, current_user.id)

@router.get("/{customer_id}", response_model=schemas.CustomerResponse)
async def get_customer(customer_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    customer = await crud.get_customer_by_id(db, customer_id, current_user.id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Customer {customer_id} not found")
    return customer

@router.post("/", response_model=schemas.CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(customer_in: schemas.CustomerCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await crud.create_customer(db, customer_in, current_user.id)

@router.put("/{customer_id}", response_model=schemas.CustomerResponse)
async def update_customer(customer_id: int, customer_in: schemas.CustomerUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    customer = await crud.update_customer(db, customer_id, customer_in, current_user.id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Customer {customer_id} not found")
    return customer

@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(customer_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not await crud.delete_customer(db, customer_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Customer {customer_id} not found")
