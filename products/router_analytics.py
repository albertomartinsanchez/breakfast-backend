from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from typing import Optional

from core.database import get_db
from auth.dependencies import get_current_user
from auth.models import User
from products import crud_analytics

router = APIRouter(prefix="/products", tags=["product-analytics"])


@router.get("/{product_id}/analytics")
async def get_product_analytics(
    product_id: int,
    start_date: Optional[date] = Query(None, description="Filter sales from this date"),
    end_date: Optional[date] = Query(None, description="Filter sales until this date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get analytics for a specific product including:
    - Sales history
    - Units sold
    - Revenue and profit
    - Top customers
    - Sales trends by date
    """
    try:
        analytics = await crud_analytics.get_product_analytics(
            db,
            product_id,
            current_user.id,
            start_date,
            end_date
        )
        return analytics
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
