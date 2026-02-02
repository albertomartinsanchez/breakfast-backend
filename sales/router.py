from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from collections import defaultdict
from datetime import datetime, time, timedelta, date as date_type
import asyncio

from core.database import get_db
from core.config import settings
from auth.dependencies import get_current_user
from auth.models import User
from sales.service import SaleService
from sales import crud_delivery, schemas
from customers.service import CustomerService
from notifications.events import notify_sale_open, notify_sale_deleted, notify_sale_closed

router = APIRouter(prefix="/sales")


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


# ============================================================================
# SALES CRUD ENDPOINTS
# ============================================================================

@router.get("/", response_model=List[schemas.SaleResponse], tags=["sales"])
async def get_sales(
    service: SaleService = Depends(get_sale_service),
    current_user: User = Depends(get_current_user)
):
    """Get all sales for the current user."""
    sales = await service.get_all(current_user.id)
    return [build_sale_response(sale) for sale in sales]


@router.get("/{sale_id}", response_model=schemas.SaleResponse, tags=["sales"])
async def get_sale(
    sale_id: int,
    service: SaleService = Depends(get_sale_service),
    current_user: User = Depends(get_current_user)
):
    """Get a specific sale by ID."""
    sale = await service.get_by_id(sale_id, current_user.id)
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sale {sale_id} not found"
        )
    return build_sale_response(sale)


@router.post("/", response_model=schemas.SaleResponse, status_code=status.HTTP_201_CREATED, tags=["sales"])
async def create_sale(
    sale_in: schemas.SaleCreate,
    db: AsyncSession = Depends(get_db),
    service: SaleService = Depends(get_sale_service),
    customer_service: CustomerService = Depends(get_customer_service),
    current_user: User = Depends(get_current_user)
):
    """Create a new sale."""
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


@router.put("/{sale_id}", response_model=schemas.SaleResponse, tags=["sales"])
async def update_sale(
    sale_id: int,
    sale_in: schemas.SaleUpdate,
    service: SaleService = Depends(get_sale_service),
    current_user: User = Depends(get_current_user)
):
    """Update a sale (replace all items)."""
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


@router.patch("/{sale_id}", status_code=status.HTTP_200_OK, tags=["sales"])
async def patch_sale(
    sale_id: int,
    updates: schemas.SalePatch,
    db: AsyncSession = Depends(get_db),
    service: SaleService = Depends(get_sale_service),
    current_user: User = Depends(get_current_user)
):
    """
    Partially update sale fields (status, date).

    Examples:
    - Close sale: {"status": "closed"}
    - Reopen sale: {"status": "draft"}
    - Change date: {"date": "2024-12-25"}
    """
    sale = await service.get_by_id(sale_id, current_user.id)
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sale {sale_id} not found"
        )

    # Track if we're closing the sale (for notification)
    is_closing = updates.status == "closed" and sale.status != "closed"

    # Validate state transitions
    if updates.status:
        valid_transitions = {
            "draft": ["closed"],
            "closed": ["draft", "in_progress"],
            "in_progress": ["completed"],
            "completed": []
        }

        if updates.status not in valid_transitions.get(sale.status, []) and updates.status != sale.status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition from '{sale.status}' to '{updates.status}'"
            )

        sale.status = updates.status

    # Update date if provided
    if updates.date:
        try:
            sale.date = date_type.fromisoformat(updates.date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use ISO format: YYYY-MM-DD"
            )

    await db.commit()
    await db.refresh(sale)

    # Send notification if sale was closed
    if is_closing:
        customer_ids = list(set(item.customer_id for item in sale.items))
        if customer_ids:
            asyncio.create_task(notify_sale_closed(db, sale_id, customer_ids))

    return {
        "message": "Sale updated successfully",
        "sale_id": sale_id,
        "status": sale.status,
        "date": str(sale.date)
    }


@router.delete("/{sale_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["sales"])
async def delete_sale(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
    service: SaleService = Depends(get_sale_service),
    current_user: User = Depends(get_current_user)
):
    """Delete a sale."""
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


@router.get("/{sale_id}/state", response_model=schemas.SaleStateResponse, tags=["sales"])
async def get_sale_state(
    sale_id: int,
    service: SaleService = Depends(get_sale_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get sale state information including:
    - Current status
    - Whether orders can be accepted
    - Hours remaining until cutoff
    - Cutoff datetime
    """
    sale = await service.get_by_id(sale_id, current_user.id)
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sale {sale_id} not found"
        )

    # Calculate cutoff time
    cutoff_time = datetime.combine(sale.date, time(0, 0)) - timedelta(hours=settings.order_cutoff_hours)
    now = datetime.now()
    hours_remaining = (cutoff_time - now).total_seconds() / 3600

    # Sale is open if within cutoff time AND status is 'draft'
    is_open = (now < cutoff_time) and (sale.status == "draft")

    return {
        "status": sale.status,
        "is_open": is_open,
        "hours_remaining": max(0, hours_remaining),
        "cutoff_time": cutoff_time
    }


# ============================================================================
# DELIVERIES ENDPOINTS
# ============================================================================

@router.post("/{sale_id}/deliveries", status_code=status.HTTP_201_CREATED, tags=["deliveries"])
async def create_delivery(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start delivery process:
    - Creates delivery steps for each customer
    - Changes sale status to 'in_progress'
    - Sale must be in 'closed' status
    """
    try:
        await crud_delivery.start_delivery(db, sale_id, current_user.id)
        return {
            "message": "Delivery created successfully",
            "sale_id": sale_id,
            "status": "in_progress"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{sale_id}/deliveries", response_model=List[schemas.DeliveryStepResponse], tags=["deliveries"])
async def get_deliveries(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get delivery route with all steps ordered by sequence."""
    try:
        delivery_route = await crud_delivery.get_delivery_route(db, sale_id, current_user.id)
        return delivery_route
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.patch("/{sale_id}/deliveries", status_code=status.HTTP_200_OK, tags=["deliveries"])
async def update_delivery_route(
    sale_id: int,
    data: schemas.DeliveryRouteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update delivery route order.

    Accepts a list of customer_id and sequence pairs to reorder the delivery route.
    Cannot be used on completed sales.
    """
    try:
        route_data = [{"customer_id": r.customer_id, "sequence": r.sequence} for r in data.route]
        await crud_delivery.update_delivery_route(db, sale_id, route_data, current_user.id)
        return {"message": "Route updated successfully", "sale_id": sale_id}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{sale_id}/deliveries/progress", response_model=schemas.DeliveryProgressResponse, tags=["deliveries"])
async def get_delivery_progress(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get delivery progress statistics."""
    try:
        progress = await crud_delivery.get_delivery_progress(db, sale_id, current_user.id)
        return progress
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.patch(
    "/{sale_id}/deliveries/customers/{customer_id}",
    status_code=status.HTTP_200_OK,
    tags=["deliveries"]
)
async def update_delivery_customer(
    sale_id: int,
    customer_id: int,
    updates: schemas.DeliveryCustomerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update delivery customer (select as next, complete, skip, or reset).

    Examples:
    - Select as next: {"is_next": true}
    - Complete: {"status": "completed", "amount_collected": 12.50}
    - Skip: {"status": "skipped", "skip_reason": "Customer not home"}
    - Reset to pending: {"status": "pending"}
    """
    try:
        # Handle is_next selection
        if updates.is_next is True:
            await crud_delivery.set_next_delivery(db, sale_id, customer_id, current_user.id)
            return {
                "message": "Customer selected as next delivery",
                "customer_id": customer_id,
                "is_next": True
            }

        # Handle status updates
        if updates.status == "completed":
            if updates.amount_collected is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="amount_collected is required when status is 'completed'"
                )

            await crud_delivery.complete_delivery(
                db, sale_id, customer_id, updates.amount_collected, current_user.id
            )

            return {
                "message": "Delivery marked as complete",
                "customer_id": customer_id,
                "status": "completed",
                "amount_collected": updates.amount_collected
            }

        elif updates.status == "skipped":
            if not updates.skip_reason:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="skip_reason is required when status is 'skipped'"
                )

            await crud_delivery.skip_delivery(
                db, sale_id, customer_id, updates.skip_reason, current_user.id
            )

            return {
                "message": "Delivery skipped",
                "customer_id": customer_id,
                "status": "skipped",
                "reason": updates.skip_reason
            }

        elif updates.status == "pending":
            await crud_delivery.reset_delivery_to_pending(
                db, sale_id, customer_id, current_user.id
            )

            return {
                "message": "Delivery reset to pending",
                "customer_id": customer_id,
                "status": "pending"
            }

        # No valid update provided
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid update provided. Use is_next or status."
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
