from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from collections import defaultdict
import asyncio

from core.database import get_db
from auth.dependencies import get_current_user
from auth.models import User
from sales.service import SaleService
from sales import schemas
from customers.service import CustomerService
from notifications.events import notify_sale_open, notify_sale_deleted

router = APIRouter(prefix="/sales", tags=["sales"])


def get_sale_service(db: AsyncSession = Depends(get_db)) -> SaleService:
    """Dependency to get SaleService instance."""
    return SaleService(db)


def get_customer_service(db: AsyncSession = Depends(get_db)) -> CustomerService:
    """Dependency to get CustomerService instance."""
    return CustomerService(db)


def build_sale_response(sale) -> schemas.SaleResponse:
    """Transform a Sale model into a SaleResponse schema."""
    customer_groups = defaultdict(list)
    for item in sale.items:
        customer_groups[item.customer_id].append(item)

    customer_sales = []
    total_benefit = 0.0
    total_revenue = 0.0

    for customer_id, items in customer_groups.items():
        products = []
        customer_benefit = 0.0
        customer_revenue = 0.0

        for item in items:
            benefit = (item.sell_price_at_sale - item.buy_price_at_sale) * item.quantity
            revenue = item.sell_price_at_sale * item.quantity
            products.append(schemas.SaleItemResponse(
                product_id=item.product_id,
                product_name=item.product.name,
                quantity=item.quantity,
                buy_price_at_sale=item.buy_price_at_sale,
                sell_price_at_sale=item.sell_price_at_sale,
                benefit=benefit
            ))
            customer_benefit += benefit
            customer_revenue += revenue

        customer_sales.append(schemas.CustomerSaleResponse(
            customer_id=customer_id,
            customer_name=items[0].customer.name,
            products=products,
            total_benefit=customer_benefit,
            total_revenue=customer_revenue
        ))
        total_benefit += customer_benefit
        total_revenue += customer_revenue

    return schemas.SaleResponse(
        id=sale.id,
        user_id=sale.user_id,
        date=sale.date,
        status=sale.status,
        customer_sales=customer_sales,
        total_benefit=total_benefit,
        total_revenue=total_revenue
    )


@router.get("/", response_model=List[schemas.SaleResponse])
async def get_sales(
    service: SaleService = Depends(get_sale_service),
    current_user: User = Depends(get_current_user)
):
    sales = await service.get_all(current_user.id)
    return [build_sale_response(sale) for sale in sales]


@router.get("/{sale_id}", response_model=schemas.SaleResponse)
async def get_sale(
    sale_id: int,
    service: SaleService = Depends(get_sale_service),
    current_user: User = Depends(get_current_user)
):
    sale = await service.get_by_id(sale_id, current_user.id)
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sale {sale_id} not found"
        )
    return build_sale_response(sale)


@router.post("/", response_model=schemas.SaleResponse, status_code=status.HTTP_201_CREATED)
async def create_sale(
    sale_in: schemas.SaleCreate,
    db: AsyncSession = Depends(get_db),
    service: SaleService = Depends(get_sale_service),
    customer_service: CustomerService = Depends(get_customer_service),
    current_user: User = Depends(get_current_user)
):
    try:
        sale = await service.create(sale_in, current_user.id)

        # Notify all customers that a new sale is open
        customers = await customer_service.get_all(current_user.id)
        if customers:
            customer_ids = [c.id for c in customers]
            sale_date = str(sale.date)
            asyncio.create_task(notify_sale_open(db, sale.id, sale_date, customer_ids))

        return build_sale_response(sale)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{sale_id}", response_model=schemas.SaleResponse)
async def update_sale(
    sale_id: int,
    sale_in: schemas.SaleUpdate,
    service: SaleService = Depends(get_sale_service),
    current_user: User = Depends(get_current_user)
):
    try:
        sale = await service.update(sale_id, sale_in, current_user.id)
        if not sale:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sale {sale_id} not found"
            )
        return build_sale_response(sale)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{sale_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sale(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
    service: SaleService = Depends(get_sale_service),
    current_user: User = Depends(get_current_user)
):
    # Get sale first to extract customer IDs and date for notification
    sale = await service.get_by_id(sale_id, current_user.id)
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sale {sale_id} not found"
        )

    # Extract customer IDs from sale items
    customer_ids = list(set(item.customer_id for item in sale.items))
    sale_date = str(sale.date)

    if not await service.delete(sale_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sale {sale_id} not found"
        )

    # Notify customers in the sale that it was deleted
    if customer_ids:
        asyncio.create_task(notify_sale_deleted(db, sale_id, sale_date, customer_ids))
