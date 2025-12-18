from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import date
from typing import Optional
from collections import defaultdict

from customers.models import Customer
from sales.models import Sale, SaleItem


async def get_customer_analytics(
    db: AsyncSession, 
    customer_id: int, 
    user_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """Get analytics for a specific customer"""
    
    # Verify customer belongs to user
    customer_result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.user_id == user_id)
    )
    customer = customer_result.scalar_one_or_none()
    if not customer:
        raise ValueError("Customer not found")
    
    # Build query for sales containing this customer
    query = (
        select(Sale)
        .join(SaleItem)
        .where(
            SaleItem.customer_id == customer_id,
            Sale.user_id == user_id
        )
        .options(
            selectinload(Sale.items).selectinload(SaleItem.product)
        )
    )
    
    # Apply date filters
    if start_date:
        query = query.where(Sale.date >= start_date)
    if end_date:
        query = query.where(Sale.date <= end_date)
    
    query = query.order_by(Sale.date.desc())
    
    result = await db.execute(query)
    sales = result.unique().scalars().all()
    
    # Calculate analytics
    purchase_history = []
    total_spent = 0.0
    total_profit = 0.0
    total_orders = len(sales)
    product_counts = defaultdict(lambda: {"count": 0, "total": 0.0})
    
    for sale in sales:
        sale_total = 0.0
        sale_profit = 0.0
        
        # Only count items for this customer
        for item in sale.items:
            if item.customer_id == customer_id:
                revenue = item.sell_price_at_sale * item.quantity
                profit = (item.sell_price_at_sale - item.buy_price_at_sale) * item.quantity
                
                sale_total += revenue
                sale_profit += profit
                
                # Track product purchases
                product_counts[item.product.name]["count"] += item.quantity
                product_counts[item.product.name]["total"] += revenue
        
        total_spent += sale_total
        total_profit += sale_profit
        
        purchase_history.append({
            "sale_id": sale.id,
            "date": sale.date.isoformat(),
            "total": round(sale_total, 2),
            "profit": round(sale_profit, 2),
            "status": sale.status
        })
    
    # Get favorite products (sorted by quantity purchased)
    favorite_products = [
        {
            "product_name": name,
            "times_purchased": data["count"],
            "total_spent": round(data["total"], 2)
        }
        for name, data in sorted(
            product_counts.items(), 
            key=lambda x: x[1]["count"], 
            reverse=True
        )
    ][:10]  # Top 10
    
    return {
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "address": customer.address,
            "phone": customer.phone
        },
        "summary": {
            "total_orders": total_orders,
            "total_spent": round(total_spent, 2),
            "total_profit_generated": round(total_profit, 2),
            "average_order_value": round(total_spent / total_orders, 2) if total_orders > 0 else 0.0,
            "first_order_date": purchase_history[-1]["date"] if purchase_history else None,
            "last_order_date": purchase_history[0]["date"] if purchase_history else None
        },
        "purchase_history": purchase_history,
        "favorite_products": favorite_products
    }
