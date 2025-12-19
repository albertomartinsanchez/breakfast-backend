import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import List

from customers.models import Customer
from customers.models_access_token import CustomerAccessToken
from sales.models import Sale, SaleItem


async def generate_tokens_for_sale(db: AsyncSession, sale_id: int, user_id: int) -> List[CustomerAccessToken]:
    """Generate access tokens for all customers who have items in this sale"""
    
    # Verify sale belongs to user
    sale_result = await db.execute(
        select(Sale).where(Sale.id == sale_id, Sale.user_id == user_id)
    )
    sale = sale_result.scalar_one_or_none()
    if not sale:
        raise ValueError("Sale not found")
    
    # Get all unique customers in this sale
    items_result = await db.execute(
        select(SaleItem.customer_id)
        .where(SaleItem.sale_id == sale_id)
        .distinct()
    )
    customer_ids = [row[0] for row in items_result.all()]
    
    if not customer_ids:
        raise ValueError("No customers found in this sale")
    
    # Delete existing tokens for this sale (regenerate)
    await db.execute(
        delete(CustomerAccessToken).where(CustomerAccessToken.sale_id == sale_id)
    )
    
    # Generate new tokens
    tokens = []
    for customer_id in customer_ids:
        token = CustomerAccessToken(
            customer_id=customer_id,
            sale_id=sale_id,
            access_token=str(uuid.uuid4())
        )
        db.add(token)
        tokens.append(token)
    
    await db.commit()
    
    # Reload with relationships
    for token in tokens:
        await db.refresh(token, ["customer", "sale"])
    
    return tokens


async def get_token_info(db: AsyncSession, sale_id: int, user_id: int) -> List[CustomerAccessToken]:
    """Get all tokens for a sale"""
    
    # Verify sale belongs to user
    sale_result = await db.execute(
        select(Sale).where(Sale.id == sale_id, Sale.user_id == user_id)
    )
    sale = sale_result.scalar_one_or_none()
    if not sale:
        raise ValueError("Sale not found")
    
    # Get tokens
    result = await db.execute(
        select(CustomerAccessToken)
        .options(
            selectinload(CustomerAccessToken.customer),
            selectinload(CustomerAccessToken.sale)
        )
        .where(CustomerAccessToken.sale_id == sale_id)
        .order_by(CustomerAccessToken.customer_id)
    )
    
    return result.scalars().all()
