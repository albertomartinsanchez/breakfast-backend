from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from typing import Optional

from core.database import get_db
from auth.dependencies import get_current_user
from auth.models import User
from analytics import crud

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
async def get_dashboard_analytics(
    start_date: Optional[date] = Query(None, description="Filter data from this date"),
    end_date: Optional[date] = Query(None, description="Filter data until this date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive dashboard analytics including:
    - Summary statistics (total sales, revenue, profit)
    - Top products by revenue
    - Top customers by revenue
    - Sales trends by date
    - Sales by status
    """
    analytics = await crud.get_dashboard_analytics(
        db,
        current_user.id,
        start_date,
        end_date
    )
    return analytics
