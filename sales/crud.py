from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from sales.models import Sale, SaleItem
from sales.schemas import SaleCreate, SaleUpdate
from products.crud import get_product_by_id
from customers.crud import get_customer_by_id

async def get_sales(db: AsyncSession, user_id: int) -> List[Sale]:
    result = await db.execute(
        select(Sale)
        .where(Sale.user_id == user_id)
        .options(
            selectinload(Sale.items).selectinload(SaleItem.product),
            selectinload(Sale.items).selectinload(SaleItem.customer)
        )
    )
    return result.scalars().all()

async def get_sale_by_id(db: AsyncSession, sale_id: int, user_id: int) -> Optional[Sale]:
    result = await db.execute(
        select(Sale)
        .where(Sale.id == sale_id, Sale.user_id == user_id)
        .options(
            selectinload(Sale.items).selectinload(SaleItem.product),
            selectinload(Sale.items).selectinload(SaleItem.customer)
        )
    )
    return result.scalar_one_or_none()

async def create_sale(db: AsyncSession, sale_in: SaleCreate, user_id: int) -> Sale:
    for cs in sale_in.customer_sales:
        if not await get_customer_by_id(db, cs.customer_id, user_id):
            raise ValueError(f"Customer {cs.customer_id} not found")
        for p in cs.products:
            if not await get_product_by_id(db, p.product_id, user_id):
                raise ValueError(f"Product {p.product_id} not found")
    
    db_sale = Sale(user_id=user_id, date=sale_in.date)
    db.add(db_sale)
    await db.flush()
    
    for cs in sale_in.customer_sales:
        for p in cs.products:
            prod = await get_product_by_id(db, p.product_id, user_id)
            db.add(SaleItem(sale_id=db_sale.id, customer_id=cs.customer_id, product_id=p.product_id, quantity=p.quantity, buy_price_at_sale=prod.buy_price, sell_price_at_sale=prod.sell_price))
    
    await db.commit()
    await db.refresh(db_sale)
    
    # Re-fetch with eager loading
    result = await db.execute(
        select(Sale)
        .where(Sale.id == db_sale.id)
        .options(
            selectinload(Sale.items).selectinload(SaleItem.product),
            selectinload(Sale.items).selectinload(SaleItem.customer)
        )
    )
    return result.scalar_one()

async def update_sale(db: AsyncSession, sale_id: int, sale_in: SaleUpdate, user_id: int) -> Optional[Sale]:
    db_sale = await get_sale_by_id(db, sale_id, user_id)
    if not db_sale:
        return None
    
    for cs in sale_in.customer_sales:
        if not await get_customer_by_id(db, cs.customer_id, user_id):
            raise ValueError(f"Customer {cs.customer_id} not found")
        for p in cs.products:
            if not await get_product_by_id(db, p.product_id, user_id):
                raise ValueError(f"Product {p.product_id} not found")
    
    db_sale.date = sale_in.date
    for item in db_sale.items:
        await db.delete(item)
    
    for cs in sale_in.customer_sales:
        for p in cs.products:
            prod = await get_product_by_id(db, p.product_id, user_id)
            db.add(SaleItem(sale_id=db_sale.id, customer_id=cs.customer_id, product_id=p.product_id, quantity=p.quantity, buy_price_at_sale=prod.buy_price, sell_price_at_sale=prod.sell_price))
    
    await db.commit()
    await db.refresh(db_sale)
    
    # Re-fetch with eager loading
    result = await db.execute(
        select(Sale)
        .where(Sale.id == db_sale.id)
        .options(
            selectinload(Sale.items).selectinload(SaleItem.product),
            selectinload(Sale.items).selectinload(SaleItem.customer)
        )
    )
    return result.scalar_one()

async def delete_sale(db: AsyncSession, sale_id: int, user_id: int) -> bool:
    db_sale = await get_sale_by_id(db, sale_id, user_id)
    if not db_sale:
        return False
    await db.delete(db_sale)
    await db.commit()
    return True