from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import date
from typing import Optional
from collections import defaultdict

from sales.models import Sale, SaleItem
from products.models import Product
from customers.models import Customer


async def get_dashboard_analytics(
    db: AsyncSession,
    user_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """Get dashboard analytics for the user"""
    
    # Build base query
    query = select(Sale).where(Sale.user_id == user_id)
    
    # Apply date filters
    if start_date:
        query = query.where(Sale.date >= start_date)
    if end_date:
        query = query.where(Sale.date <= end_date)
    
    query = query.options(
        selectinload(Sale.items).selectinload(SaleItem.product),
        selectinload(Sale.items).selectinload(SaleItem.customer)
    )
    
    result = await db.execute(query)
    sales = result.scalars().all()
    
    # Calculate totals
    total_sales = len(sales)
    total_revenue = 0.0
    total_profit = 0.0
    product_performance = defaultdict(lambda: {"quantity": 0, "revenue": 0.0, "profit": 0.0})
    customer_performance = defaultdict(lambda: {"orders": 0, "revenue": 0.0, "profit": 0.0})
    sales_by_date = defaultdict(lambda: {"count": 0, "revenue": 0.0, "profit": 0.0})
    sales_by_status = defaultdict(int)
    
    for sale in sales:
        sale_revenue = 0.0
        sale_profit = 0.0
        
        # Track by status
        sales_by_status[sale.status] += 1
        
        for item in sale.items:
            revenue = item.sell_price_at_sale * item.quantity
            profit = (item.sell_price_at_sale - item.buy_price_at_sale) * item.quantity
            
            sale_revenue += revenue
            sale_profit += profit
            
            # Product performance
            product_performance[item.product.name]["quantity"] += item.quantity
            product_performance[item.product.name]["revenue"] += revenue
            product_performance[item.product.name]["profit"] += profit
            
            # Customer performance
            customer_performance[item.customer.name]["revenue"] += revenue
            customer_performance[item.customer.name]["profit"] += profit
        
        # Track unique customers per sale
        unique_customers = set(item.customer_id for item in sale.items)
        for customer_id in unique_customers:
            customer_name = next(item.customer.name for item in sale.items if item.customer_id == customer_id)
            customer_performance[customer_name]["orders"] += 1
        
        total_revenue += sale_revenue
        total_profit += sale_profit
        
        # Sales by date
        date_key = sale.date.isoformat()
        sales_by_date[date_key]["count"] += 1
        sales_by_date[date_key]["revenue"] += sale_revenue
        sales_by_date[date_key]["profit"] += sale_profit
    
    # Get counts for products and customers
    products_result = await db.execute(
        select(func.count(Product.id)).where(Product.user_id == user_id)
    )
    total_products = products_result.scalar()
    
    customers_result = await db.execute(
        select(func.count(Customer.id)).where(Customer.user_id == user_id)
    )
    total_customers = customers_result.scalar()
    
    # Top products (by revenue)
    top_products = [
        {
            "product_name": name,
            "units_sold": data["quantity"],
            "revenue": round(data["revenue"], 2),
            "profit": round(data["profit"], 2)
        }
        for name, data in sorted(
            product_performance.items(),
            key=lambda x: x[1]["revenue"],
            reverse=True
        )
    ][:10]
    
    # Top customers (by revenue)
    top_customers = [
        {
            "customer_name": name,
            "orders": data["orders"],
            "revenue": round(data["revenue"], 2),
            "profit": round(data["profit"], 2)
        }
        for name, data in sorted(
            customer_performance.items(),
            key=lambda x: x[1]["revenue"],
            reverse=True
        )
    ][:10]
    
    # Sales by date (sorted)
    sales_by_date_list = [
        {
            "date": date_str,
            "count": data["count"],
            "revenue": round(data["revenue"], 2),
            "profit": round(data["profit"], 2)
        }
        for date_str, data in sorted(sales_by_date.items(), reverse=True)
    ]
    
    return {
        "summary": {
            "total_sales": total_sales,
            "total_revenue": round(total_revenue, 2),
            "total_profit": round(total_profit, 2),
            "total_products": total_products,
            "total_customers": total_customers,
            "average_sale_revenue": round(total_revenue / total_sales, 2) if total_sales > 0 else 0.0,
            "average_sale_profit": round(total_profit / total_sales, 2) if total_sales > 0 else 0.0,
            "profit_margin": round((total_profit / total_revenue * 100), 2) if total_revenue > 0 else 0.0
        },
        "sales_by_status": dict(sales_by_status),
        "top_products": top_products,
        "top_customers": top_customers,
        "sales_by_date": sales_by_date_list
    }
