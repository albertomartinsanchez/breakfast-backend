from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import func
from typing import List, Dict
from datetime import datetime

from customers.models_access_token import CustomerAccessToken
from sales.models import Sale, SaleItem
from products.models import Product


async def validate_and_get_access(db: AsyncSession, token: str) -> CustomerAccessToken:
    """Validate token and return access info"""
    
    result = await db.execute(
        select(CustomerAccessToken)
        .options(
            selectinload(CustomerAccessToken.customer),
            selectinload(CustomerAccessToken.sale)
        )
        .where(CustomerAccessToken.access_token == token)
    )
    
    access = result.scalar_one_or_none()
    if not access:
        raise ValueError("Invalid access token")
    
    # Update last accessed time
    access.last_accessed_at = func.now()
    await db.commit()
    
    return access


async def get_public_order_view(db: AsyncSession, token: str) -> Dict:
    """Get order view for customer"""
    
    # Validate token
    access = await validate_and_get_access(db, token)
    
    # Get all products (user's products)
    products_result = await db.execute(
        select(Product)
        .where(Product.user_id == access.sale.user_id)
        .order_by(Product.name)
    )
    products = products_result.scalars().all()
    
    # Get customer's current order items
    items_result = await db.execute(
        select(SaleItem)
        .options(selectinload(SaleItem.product))
        .where(
            SaleItem.sale_id == access.sale_id,
            SaleItem.customer_id == access.customer_id
        )
    )
    items = items_result.scalars().all()
    
    # Build current order
    current_order = []
    order_total = 0.0
    
    for item in items:
        total_price = item.sell_price_at_sale * item.quantity
        order_total += total_price
        
        current_order.append({
            "product_id": item.product_id,
            "product_name": item.product.name,
            "quantity": item.quantity,
            "unit_price": item.sell_price_at_sale,
            "total_price": total_price
        })
    
    # Determine if customer can edit
    is_open = access.sale.status == "draft"
    
    # Build message
    message = None
    if access.sale.status == "closed":
        message = "This order is closed. You can no longer make changes."
    elif access.sale.status == "in_progress":
        message = "Delivery is in progress! Check delivery status below."
    elif access.sale.status == "completed":
        message = "This sale has been completed."
    
    return {
        "sale_id": access.sale_id,
        "sale_date": access.sale.date.isoformat(),
        "sale_status": access.sale.status,
        "is_open": is_open,
        "customer_id": access.customer_id,
        "customer_name": access.customer.name,
        "available_products": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "sell_price": p.sell_price
            }
            for p in products
        ],
        "current_order": current_order,
        "order_total": order_total,
        "message": message
    }


async def save_customer_order(
    db: AsyncSession, 
    token: str, 
    items: List[Dict]
) -> Dict:
    """Save customer's order"""
    
    # Validate token
    access = await validate_and_get_access(db, token)
    
    # Check if sale is open
    if access.sale.status != "draft":
        raise ValueError("This sale is closed and cannot be modified")
    
    # Delete existing items for this customer in this sale
    await db.execute(
        delete(SaleItem).where(
            SaleItem.sale_id == access.sale_id,
            SaleItem.customer_id == access.customer_id
        )
    )
    
    # Add new items
    order_total = 0.0
    items_count = 0
    
    for item_data in items:
        # Skip if quantity is 0
        if item_data["quantity"] <= 0:
            continue
        
        # Get product to get current prices
        product_result = await db.execute(
            select(Product).where(
                Product.id == item_data["product_id"],
                Product.user_id == access.sale.user_id
            )
        )
        product = product_result.scalar_one_or_none()
        
        if not product:
            raise ValueError(f"Product {item_data['product_id']} not found")
        
        # Create sale item
        sale_item = SaleItem(
            sale_id=access.sale_id,
            customer_id=access.customer_id,
            product_id=product.id,
            quantity=item_data["quantity"],
            buy_price_at_sale=product.buy_price,
            sell_price_at_sale=product.sell_price
        )
        db.add(sale_item)
        
        order_total += product.sell_price * item_data["quantity"]
        items_count += 1
    
    await db.commit()
    
    return {
        "success": True,
        "message": "Order saved successfully!" if items_count > 0 else "Order cleared!",
        "order_total": order_total,
        "items_count": items_count
    }
