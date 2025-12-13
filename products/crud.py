from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from products.models import Product
from products.schemas import ProductCreate, ProductUpdate


async def get_products(db: AsyncSession) -> List[Product]:
    result = await db.execute(select(Product))
    return result.scalars().all()


async def get_product_by_id(db: AsyncSession, product_id: int) -> Optional[Product]:
    result = await db.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()


async def create_product(db: AsyncSession, product_in: ProductCreate) -> Product:
    db_product = Product(
        name=product_in.name,
        description=product_in.description,
        buy_price=product_in.buy_price,
        sell_price=product_in.sell_price
    )
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product


async def update_product(db: AsyncSession, product_id: int, product_in: ProductUpdate) -> Optional[Product]:
    db_product = await get_product_by_id(db, product_id)
    if not db_product:
        return None
    
    db_product.name = product_in.name
    db_product.description = product_in.description
    db_product.buy_price = product_in.buy_price
    db_product.sell_price = product_in.sell_price
    
    await db.commit()
    await db.refresh(db_product)
    return db_product


async def delete_product(db: AsyncSession, product_id: int) -> bool:
    db_product = await get_product_by_id(db, product_id)
    if not db_product:
        return False
    
    await db.delete(db_product)
    await db.commit()
    return True
