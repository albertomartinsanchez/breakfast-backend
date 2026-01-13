import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db, async_session_maker
from public_orders import crud
from public_orders.schemas import (
    PublicCustomerInfo,
    PublicSaleDetail,
    UpdateOrderRequest,
    UpdateOrderResponse,
    DeliveryStatusResponse
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

@router.get("/{token}/sales/{sale_id}/delivery-status", response_model=DeliveryStatusResponse)
async def get_delivery_status(
    token: str,
    sale_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Public endpoint - no authentication required.

    Get customer's delivery status and position in queue.
    """
    try:
        data = await crud.get_customer_delivery_status(db, token, sale_id)
        return DeliveryStatusResponse(**data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{token}/sales/{sale_id}/delivery-status/stream")
async def stream_delivery_status(
    token: str,
    sale_id: int,
    request: Request
):
    """
    Public endpoint - no authentication required.

    SSE stream for real-time delivery status updates.
    Sends updates when delivery status changes.
    """
    async def event_generator():
        last_data = None

        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            try:
                async with async_session_maker() as db:
                    data = await crud.get_customer_delivery_status(db, token, sale_id)

                    # Send update if data changed or first message
                    if data != last_data:
                        last_data = data
                        yield f"data: {json.dumps(data)}\n\n"

            except ValueError:
                # Token or sale invalid - close the stream
                yield f"data: {json.dumps({'error': 'invalid_request'})}\n\n"
                break

            # Wait before next check
            await asyncio.sleep(5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )