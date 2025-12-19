from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from public_orders import crud
from public_orders.schemas import PublicOrderView, SaveOrderRequest, SaveOrderResponse

router = APIRouter(prefix="/order", tags=["public-orders"])


@router.get("/{token}", response_model=PublicOrderView)
async def get_order_view(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Public endpoint - no authentication required.
    
    Get order view for a customer using their access token.
    Shows available products and customer's current order.
    
    - Works with any valid token
    - Updates last_accessed_at timestamp
    - Returns read-only view if sale is closed
    """
    try:
        order_view = await crud.get_public_order_view(db, token)
        return order_view
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{token}", response_model=SaveOrderResponse)
async def save_order(
    token: str,
    order: SaveOrderRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Public endpoint - no authentication required.
    
    Save customer's order using their access token.
    
    - Only works if sale status is "draft"
    - Replaces existing order completely
    - Items with quantity 0 are ignored
    - Empty items list clears the order
    """
    try:
        # Convert Pydantic models to dicts
        items_dicts = [item.model_dump() for item in order.items]
        result = await crud.save_customer_order(db, token, items_dicts)
        return SaveOrderResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
