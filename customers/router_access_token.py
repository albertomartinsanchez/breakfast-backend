from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from core.database import get_db
from auth.dependencies import get_current_user
from auth.models import User
from customers import crud_access_token
from public_orders.schemas import GenerateTokensResponse, TokenInfo

router = APIRouter(prefix="/sales", tags=["access-tokens"])


@router.post("/{sale_id}/generate-tokens", response_model=GenerateTokensResponse)
async def generate_access_tokens(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate access tokens for all customers in a sale.
    This creates unique URLs that customers can use to place orders.
    
    - Tokens are regenerated each time (old tokens are invalidated)
    - Only customers who have items in the sale get tokens
    - Returns list of tokens with customer info for sharing
    """
    try:
        tokens = await crud_access_token.generate_tokens_for_sale(db, sale_id, current_user.id)
        
        # Build response
        token_infos = [
            TokenInfo(
                customer_id=token.customer_id,
                customer_name=token.customer.name,
                access_token=token.access_token,
                access_url=f"/order/{token.access_token}"  # Frontend will prepend domain
            )
            for token in tokens
        ]
        
        return GenerateTokensResponse(
            sale_id=sale_id,
            sale_date=tokens[0].sale.date.isoformat(),
            tokens=token_infos,
            total_customers=len(token_infos)
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{sale_id}/tokens", response_model=List[TokenInfo])
async def get_sale_tokens(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get existing tokens for a sale.
    Useful for viewing/resending tokens without regenerating.
    """
    try:
        tokens = await crud_access_token.get_token_info(db, sale_id, current_user.id)
        
        return [
            TokenInfo(
                customer_id=token.customer_id,
                customer_name=token.customer.name,
                access_token=token.access_token,
                access_url=f"/order/{token.access_token}"
            )
            for token in tokens
        ]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
