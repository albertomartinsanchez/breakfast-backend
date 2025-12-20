from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import Dict, List
from datetime import datetime

from customers.models_access_token import CustomerAccessToken
from sales.models import Sale, SaleItem
from products.models import Product


async def validate_token(db: AsyncSession, token: str) -> CustomerAccessToken:
    """Validate customer token"""
    result = await db.execute(
        select(CustomerAccessToken)
        .options(selectinload(CustomerAccessToken.customer))
        .where(CustomerAccessToken.access_token == token)
    )
    
    access = result.scalar_one_or_none()
    if not access:
        raise ValueError("Invalid access token")
    
    # Update last accessed
    access.last_accessed_at = datetime.utcnow()
    await db.commit()
    
    return access


async def get_customer_sales_list(db: AsyncSession, token: str) -> Dict:
    """Get list of all sales for customer"""
    access = await validate_token(db, token)
    
    # Get all sales for this user
    sales_result = await db.execute(
        select(Sale)
        .where(Sale.user_id == access.customer.user_id)
        .order_by(Sale.date.desc())
    )
    sales = sales_result.scalars().all()
    
    # Build sale list
    sale_items = []
    for sale in sales:
        is_open = sale.status == "draft"
        sale_items.append({
            "id": sale.id,
            "date": sale.date,
            "status": sale.status,
            "is_open": is_open
        })
    
    return {
        "customer_id": access.customer_id,
        "customer_name": access.customer.name,
        "sales": sale_items
    }


async def get_sale_for_ordering(db: AsyncSession, token: str, sale_id: int) -> Dict:
    """Get sale details for customer to place order"""
    access = await validate_token(db, token)
    
    # Get sale
    sale_result = await db.execute(
        select(Sale).where(
            Sale.id == sale_id,
            Sale.user_id == access.customer.user_id
        )
    )
    sale = sale_result.scalar_one_or_none()
    if not sale:
        raise ValueError("Sale not found")
    
    # Get available products
    products_result = await db.execute(
        select(Product)
        .where(Product.user_id == access.customer.user_id)
        .order_by(Product.name)
    )
    products = products_result.scalars().all()
    
    # Get customer's current order
    items_result = await db.execute(
        select(SaleItem)
        .options(selectinload(SaleItem.product))
        .where(
            SaleItem.sale_id == sale_id,
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
    
    # Determine if can edit
    is_open = sale.status == "draft"
    
    # Build message
    message = None
    if sale.status == "closed":
        message = "This sale is closed. You cannot make changes."
    elif sale.status == "in_progress":
        message = "Delivery is in progress!"
    elif sale.status == "completed":
        message = "This sale has been completed."
    
    return {
        "sale_id": sale_id,
        "sale_date": sale.date,
        "sale_status": sale.status,
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


async def update_customer_order(
    db: AsyncSession,
    token: str,
    sale_id: int,
    items: List[Dict]
) -> Dict:
    """Update customer's order for a sale"""
    access = await validate_token(db, token)
    
    # Get sale
    sale_result = await db.execute(
        select(Sale).where(
            Sale.id == sale_id,
            Sale.user_id == access.customer.user_id
        )
    )
    sale = sale_result.scalar_one_or_none()
    if not sale:
        raise ValueError("Sale not found")
    
    # Check if sale is open
    if sale.status != "draft":
        raise ValueError("This sale is closed and cannot be modified")
    
    # Delete existing items for this customer
    await db.execute(
        delete(SaleItem).where(
            SaleItem.sale_id == sale_id,
            SaleItem.customer_id == access.customer_id
        )
    )
    
    # Add new items
    order_total = 0.0
    items_count = 0
    
    for item_data in items:
        if item_data["quantity"] <= 0:
            continue
        
        # Get product
        product_result = await db.execute(
            select(Product).where(
                Product.id == item_data["product_id"],
                Product.user_id == access.customer.user_id
            )
        )
        product = product_result.scalar_one_or_none()
        
        if not product:
            raise ValueError(f"Product {item_data['product_id']} not found")
        
        # Create sale item
        sale_item = SaleItem(
            sale_id=sale_id,
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
        "message": "Order updated successfully!" if items_count > 0 else "Order cleared!",
        "order_total": order_total,
        "items_count": items_count
    }

async def get_customer_delivery_status(db: AsyncSession, token: str, sale_id: int) -> Dict:
    """Get customer's delivery status and position in queue"""
    access = await validate_token(db, token)
    
    # Get sale
    sale_result = await db.execute(
        select(Sale).where(
            Sale.id == sale_id,
            Sale.user_id == access.customer.user_id
        )
    )
    sale = sale_result.scalar_one_or_none()
    if not sale:
        raise ValueError("Sale not found")
    
    # Base response
    response = {
        "sale_status": sale.status,
        "customer_delivery_status": "pending",
        "position_in_queue": None,
        "deliveries_ahead": None,
        "estimated_minutes": None,
        "completed_at": None,
        "amount_collected": None,
        "skip_reason": None
    }
    
    # Only calculate delivery info if sale is in_progress or completed
    if sale.status not in ["in_progress", "completed"]:
        return response
    
    # Get customer's delivery step
    from sales.models import SaleDeliveryStep
    
    delivery_result = await db.execute(
        select(SaleDeliveryStep)
        .where(
            SaleDeliveryStep.sale_id == sale_id,
            SaleDeliveryStep.customer_id == access.customer_id
        )
    )
    delivery_step = delivery_result.scalar_one_or_none()
    
    if not delivery_step:
        # Customer not in delivery route
        return response
    
    # Update delivery status
    response["customer_delivery_status"] = delivery_step.status
    
    if delivery_step.status == "completed":
        response["completed_at"] = delivery_step.completed_at.isoformat() if delivery_step.completed_at else None
        response["amount_collected"] = delivery_step.amount_collected
    elif delivery_step.status == "skipped":
        response["skip_reason"] = delivery_step.skip_reason
    elif delivery_step.status == "pending":
        # Calculate position in queue
        all_deliveries_result = await db.execute(
            select(SaleDeliveryStep)
            .where(SaleDeliveryStep.sale_id == sale_id)
            .order_by(SaleDeliveryStep.sequence_order)
        )
        all_deliveries = all_deliveries_result.scalars().all()
        
        # Find position
        for idx, d in enumerate(all_deliveries):
            if d.id == delivery_step.id:
                response["position_in_queue"] = idx + 1
                break
        
        # Count deliveries ahead that are still pending
        deliveries_ahead = 0
        for d in all_deliveries:
            if d.sequence_order < delivery_step.sequence_order and d.status == "pending":
                deliveries_ahead += 1
        
        response["deliveries_ahead"] = deliveries_ahead
        
        # Calculate estimated time (simple: 5 min per delivery ahead)
        # TODO: Could calculate from actual completed delivery times
        if deliveries_ahead > 0:
            response["estimated_minutes"] = deliveries_ahead * 5
        else:
            response["estimated_minutes"] = 2  # Next up!
    
    return response