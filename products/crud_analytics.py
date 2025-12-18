from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import date
from typing import Optional
from collections import defaultdict

from products.models import Product
from sales.models import Sale, SaleItem


async def get_product_analytics(
    db: AsyncSession, 
    product_id: int, 
    user_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """Get analytics for a specific product"""
    
    # Verify product belongs to user
    product_result = await db.execute(
        select(Product).where(Product.id == product_id, Product.user_id == user_id)
    )
    product = product_result.scalar_one_or_none()
    if not product:
        raise ValueError("Product not found")
    
    # Build query for sale items containing this product
    query = (
        select(SaleItem)
        .join(Sale)
        .where(
            SaleItem.product_id == product_id,
            Sale.user_id == user_id
        )
        .options(
            selectinload(SaleItem.sale),
            selectinload(SaleItem.customer)
        )
    )
    
    # Apply date filters
    if start_date:
        query = query.where(Sale.date >= start_date)
    if end_date:
        query = query.where(Sale.date <= end_date)
    
    query = query.order_by(Sale.date.desc())
    
    result = await db.execute(query)
    sale_items = result.scalars().all()
    
    # Calculate analytics
    sales_history = []
    total_units_sold = 0
    total_revenue = 0.0
    total_profit = 0.0
    customer_purchases = defaultdict(int)
    sales_by_date = defaultdict(lambda: {"quantity": 0, "revenue": 0.0})
    
    for item in sale_items:
        revenue = item.sell_price_at_sale * item.quantity
        profit = (item.sell_price_at_sale - item.buy_price_at_sale) * item.quantity
        
        total_units_sold += item.quantity
        total_revenue += revenue
        total_profit += profit
        
        # Track customer purchases
        customer_purchases[item.customer.name] += item.quantity
        
        # Track sales by date
        date_key = item.sale.date.isoformat()
        sales_by_date[date_key]["quantity"] += item.quantity
        sales_by_date[date_key]["revenue"] += revenue
        
        sales_history.append({
            "sale_id": item.sale_id,
            "date": item.sale.date.isoformat(),
            "customer_name": item.customer.name,
            "quantity": item.quantity,
            "unit_price": item.sell_price_at_sale,
            "revenue": round(revenue, 2),
            "profit": round(profit, 2)
        })
    
    # Get top customers
    top_customers = [
        {
            "customer_name": name,
            "units_purchased": quantity
        }
        for name, quantity in sorted(
            customer_purchases.items(),
            key=lambda x: x[1],
            reverse=True
        )
    ][:10]  # Top 10
    
    # Format sales by date
    sales_by_date_list = [
        {
            "date": date_str,
            "quantity": data["quantity"],
            "revenue": round(data["revenue"], 2)
        }
        for date_str, data in sorted(sales_by_date.items(), reverse=True)
    ]
    
    # Calculate average metrics
    num_sales = len(set(item.sale_id for item in sale_items))
    
    return {
        "product": {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "buy_price": product.buy_price,
            "sell_price": product.sell_price,
            "profit_margin": round((product.sell_price - product.buy_price) / product.sell_price * 100, 2) if product.sell_price > 0 else 0
        },
        "summary": {
            "total_units_sold": total_units_sold,
            "total_revenue": round(total_revenue, 2),
            "total_profit": round(total_profit, 2),
            "num_sales": num_sales,
            "average_units_per_sale": round(total_units_sold / num_sales, 2) if num_sales > 0 else 0.0,
            "average_revenue_per_sale": round(total_revenue / num_sales, 2) if num_sales > 0 else 0.0
        },
        "sales_history": sales_history,
        "top_customers": top_customers,
        "sales_by_date": sales_by_date_list
    }
