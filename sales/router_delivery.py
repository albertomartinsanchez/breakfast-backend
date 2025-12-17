from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Literal
from datetime import datetime, time, timedelta
from pydantic import BaseModel, Field

from core.database import get_db
from core.config import settings
from auth.dependencies import get_current_user
from auth.models import User
from sales import crud_delivery
from sales.schemas import (
    DeliveryStepResponse,
    DeliveryProgressResponse,
    CustomerSequence,
)

router = APIRouter(prefix="/sales", tags=["sales", "delivery"])


# ============================================================================
# SCHEMAS
# ============================================================================

class SaleUpdateRequest(BaseModel):
    """Schema for updating sale fields via PATCH"""
    status: Optional[Literal["draft", "closed", "in_progress", "completed"]] = None
    date: Optional[str] = None  # ISO date string


class SaleStateResponse(BaseModel):
    """Response for sale state information"""
    status: str
    is_open: bool
    hours_remaining: float
    cutoff_time: datetime


class DeliveryRouteUpdate(BaseModel):
    """Schema for reordering delivery route"""
    route: List[CustomerSequence]


class DeliveryCustomerStatusUpdate(BaseModel):
    """Schema for updating delivery customer status"""
    status: Literal["completed", "skipped", "pending"]
    amount_collected: Optional[float] = Field(None, gt=0, description="Amount collected (required for completed)")
    skip_reason: Optional[str] = Field(None, min_length=1, description="Reason for skipping (required for skipped)")


# ============================================================================
# SALE STATE ENDPOINTS
# ============================================================================

@router.get("/{sale_id}/state", response_model=SaleStateResponse)
async def get_sale_state(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get sale state information including:
    - Current status
    - Whether orders can be accepted
    - Hours remaining until cutoff
    - Cutoff datetime
    """
    from sales.crud import get_sale_by_id
    
    sale = await get_sale_by_id(db, sale_id, current_user.id)
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


@router.patch("/{sale_id}", status_code=status.HTTP_200_OK)
async def update_sale(
    sale_id: int,
    updates: SaleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update sale fields (status, date, etc.)
    
    Examples:
    - Close sale: {"status": "closed"}
    - Reopen sale: {"status": "draft"}
    - Change date: {"date": "2024-12-25"}
    - Multiple: {"status": "closed", "date": "2024-12-25"}
    """
    from sales.crud import get_sale_by_id
    from datetime import date as date_type
    
    # Get sale
    sale = await get_sale_by_id(db, sale_id, current_user.id)
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sale {sale_id} not found"
        )
    
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
    
    return {
        "message": "Sale updated successfully",
        "sale_id": sale_id,
        "status": sale.status,
        "date": str(sale.date)
    }


# ============================================================================
# DELIVERY MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/{sale_id}/delivery", status_code=status.HTTP_201_CREATED)
async def create_delivery(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create/Start delivery process:
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


@router.get("/{sale_id}/delivery", response_model=List[DeliveryStepResponse])
async def get_delivery(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get delivery route with all steps ordered by sequence"""
    try:
        delivery_route = await crud_delivery.get_delivery_route(db, sale_id, current_user.id)
        return delivery_route
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.patch("/{sale_id}/delivery", status_code=status.HTTP_200_OK)
async def update_delivery(
    sale_id: int,
    updates: DeliveryRouteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update the delivery route (reorder customers)
    
    Body example:
    {
      "route": [
        {"customer_id": 1, "sequence": 1},
        {"customer_id": 3, "sequence": 2},
        {"customer_id": 2, "sequence": 3}
      ]
    }
    """
    try:
        # Convert to dict format
        route_dict = [{"customer_id": item.customer_id, "sequence": item.sequence} for item in updates.route]
        await crud_delivery.update_delivery_route(db, sale_id, route_dict, current_user.id)
        return {"message": "Delivery route updated successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{sale_id}/delivery/progress", response_model=DeliveryProgressResponse)
async def get_delivery_progress(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get delivery progress statistics"""
    try:
        progress = await crud_delivery.get_delivery_progress(db, sale_id, current_user.id)
        return progress
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.patch("/{sale_id}/delivery/customers/{customer_id}/status", status_code=status.HTTP_200_OK)
async def update_delivery_customer_status(
    sale_id: int,
    customer_id: int,
    status_update: DeliveryCustomerStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update delivery customer status
    
    Examples:
    - Complete: {"status": "completed", "amount_collected": 12.50}
    - Skip: {"status": "skipped", "skip_reason": "Customer not home"}
    - Reset to pending: {"status": "pending"}
    """
    try:
        # Validate required fields
        if status_update.status == "completed":
            if status_update.amount_collected is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="amount_collected is required when status is 'completed'"
                )
            
            await crud_delivery.complete_delivery(
                db,
                sale_id,
                customer_id,
                status_update.amount_collected,
                current_user.id
            )
            
            return {
                "message": "Delivery marked as complete",
                "customer_id": customer_id,
                "status": "completed",
                "amount_collected": status_update.amount_collected
            }
        
        elif status_update.status == "skipped":
            if not status_update.skip_reason:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="skip_reason is required when status is 'skipped'"
                )
            
            await crud_delivery.skip_delivery(
                db,
                sale_id,
                customer_id,
                status_update.skip_reason,
                current_user.id
            )
            
            return {
                "message": "Delivery skipped",
                "customer_id": customer_id,
                "status": "skipped",
                "reason": status_update.skip_reason
            }
        
        elif status_update.status == "pending":
            # Reset to pending (useful if accidentally marked wrong)
            await crud_delivery.reset_delivery_to_pending(
                db,
                sale_id,
                customer_id,
                current_user.id
            )
            
            return {
                "message": "Delivery reset to pending",
                "customer_id": customer_id,
                "status": "pending"
            }
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_update.status}"
            )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
