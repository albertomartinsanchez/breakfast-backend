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
from notifications.schemas import DeviceRegisterRequest, DeviceRegisterResponse
from notifications import crud as notifications_crud

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


@router.get("/{token}/sales/status-stream")
async def stream_sales_status(
    token: str,
    request: Request
):
    """
    Public endpoint - no authentication required.

    SSE stream for real-time sales status updates.
    Sends updates when any sale status changes.
    """
    async def event_generator():
        last_json = None

        while True:
            if await request.is_disconnected():
                break

            try:
                async with async_session_maker() as db:
                    await db.connection()
                    data = await crud.get_customer_sales_statuses(db, token)
                    data_json = json.dumps(data, sort_keys=True)

                    if data_json != last_json:
                        last_json = data_json
                        yield f"data: {data_json}\n\n"

            except ValueError:
                yield f"data: {json.dumps({'error': 'invalid_request'})}\n\n"
                break

            await asyncio.sleep(3)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


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
        last_json = None

        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            try:
                async with async_session_maker() as db:
                    # Force fresh read by beginning a new transaction
                    await db.connection()
                    data = await crud.get_customer_delivery_status(db, token, sale_id)
                    data_json = json.dumps(data, sort_keys=True)

                    # Send update if data changed or first message
                    if data_json != last_json:
                        last_json = data_json
                        yield f"data: {data_json}\n\n"

            except ValueError:
                # Token or sale invalid - close the stream
                yield f"data: {json.dumps({'error': 'invalid_request'})}\n\n"
                break

            # Wait before next check
            await asyncio.sleep(3)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/{token}/devices", response_model=DeviceRegisterResponse)
async def register_device(
    token: str,
    device: DeviceRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Public endpoint - no authentication required.

    Register a device for push notifications.
    The device token is typically obtained from Firebase Cloud Messaging.
    """
    # Get customer ID from token
    customer_id = await notifications_crud.get_customer_id_by_token(db, token)
    if not customer_id:
        raise HTTPException(status_code=404, detail="Invalid customer token")

    await notifications_crud.register_device(
        db,
        customer_id=customer_id,
        device_token=device.device_token,
        device_type=device.device_type
    )

    return DeviceRegisterResponse(
        success=True,
        message="Device registered successfully"
    )


@router.delete("/{token}/devices", response_model=DeviceRegisterResponse)
async def unregister_device(
    token: str,
    device: DeviceRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Public endpoint - no authentication required.

    Unregister a device from push notifications.
    """
    # Verify token is valid
    customer_id = await notifications_crud.get_customer_id_by_token(db, token)
    if not customer_id:
        raise HTTPException(status_code=404, detail="Invalid customer token")

    success = await notifications_crud.unregister_device(db, device.device_token)

    return DeviceRegisterResponse(
        success=success,
        message="Device unregistered" if success else "Device not found"
    )