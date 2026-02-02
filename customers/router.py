from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from core.database import get_db
from auth.dependencies import get_current_user
from auth.models import User
from customers.service import CustomerService
from customers import schemas

router = APIRouter(prefix="/customers", tags=["customers"])


def get_customer_service(db: AsyncSession = Depends(get_db)) -> CustomerService:
    """Dependency to get CustomerService instance."""
    return CustomerService(db)


@router.get("/", response_model=List[schemas.CustomerResponse])
async def get_customers(
    service: CustomerService = Depends(get_customer_service),
    current_user: User = Depends(get_current_user)
):
    return await service.get_all(current_user.id)


@router.get("/{customer_id}", response_model=schemas.CustomerResponse)
async def get_customer(
    customer_id: int,
    service: CustomerService = Depends(get_customer_service),
    current_user: User = Depends(get_current_user)
):
    customer = await service.get_by_id(customer_id, current_user.id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found"
        )
    return customer


@router.post("/", response_model=schemas.CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_in: schemas.CustomerCreate,
    service: CustomerService = Depends(get_customer_service),
    current_user: User = Depends(get_current_user)
):
    return await service.create(customer_in, current_user.id)


@router.put("/{customer_id}", response_model=schemas.CustomerResponse)
async def update_customer(
    customer_id: int,
    customer_in: schemas.CustomerUpdate,
    service: CustomerService = Depends(get_customer_service),
    current_user: User = Depends(get_current_user)
):
    customer = await service.update(customer_id, customer_in, current_user.id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found"
        )
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: int,
    service: CustomerService = Depends(get_customer_service),
    current_user: User = Depends(get_current_user)
):
    if not await service.delete(customer_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found"
        )
