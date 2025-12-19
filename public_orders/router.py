from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from public_orders import crud
from public_orders.schemas import (
    PublicCustomerInfo,
    PublicSaleDetail,
    UpdateOrderRequest,
    UpdateOrderResponse
)

router = APIRouter(prefix="/customer", tags=["public-customer"])


@router.get("/{token}", response_model=PublicCustomerInfo)
async def get_customer_view(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Public endpoint - no authentication required.
    
    Get customer's personal page showing all sales.
    """
    try:
        data = await crud.get_customer_sales_list(db, token)
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{token}/sales/{sale_id}", response_model=PublicSaleDetail)
async def get_sale_for_order(
    token: str,
    sale_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Public endpoint - no authentication required.
    
    Get sale details for customer to place/view order.
    """
    try:
        data = await crud.get_sale_for_ordering(db, token, sale_id)
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{token}/sales/{sale_id}/order", response_model=UpdateOrderResponse)
async def update_order(
    token: str,
    sale_id: int,
    order: UpdateOrderRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Public endpoint - no authentication required.
    
    Update customer's order for a sale.
    Only works if sale is open (draft status).
    """
    try:
        items_dicts = [item.model_dump() for item in order.items]
        result = await crud.update_customer_order(db, token, sale_id, items_dicts)
        return UpdateOrderResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
