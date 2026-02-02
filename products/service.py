from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from products.models import Product
from products.repository import ProductRepository
from products.schemas import ProductCreate, ProductUpdate


class ProductService:
    """
    Service layer for Product business logic.

    This class orchestrates operations using repositories and contains
    all business logic such as validation, price calculations, etc.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.product_repo = ProductRepository(db)

    async def get_all(self, user_id: int) -> List[Product]:
        """Get all products for a user."""
        return await self.product_repo.get_all(user_id)

    async def get_by_id(self, product_id: int, user_id: int) -> Optional[Product]:
        """Get a product by ID."""
        return await self.product_repo.get_by_id(product_id, user_id)

    async def create(self, product_in: ProductCreate, user_id: int) -> Product:
        """Create a new product."""
        product = Product(
            user_id=user_id,
            name=product_in.name,
            description=product_in.description,
            buy_price=product_in.buy_price,
            sell_price=product_in.sell_price
        )

        await self.product_repo.add(product)
        await self.product_repo.commit()
        await self.product_repo.refresh(product)

        return product

    async def update(
        self, product_id: int, product_in: ProductUpdate, user_id: int
    ) -> Optional[Product]:
        """Update an existing product."""
        product = await self.product_repo.get_by_id(product_id, user_id)
        if not product:
            return None

        product.name = product_in.name
        product.description = product_in.description
        product.buy_price = product_in.buy_price
        product.sell_price = product_in.sell_price

        await self.product_repo.commit()
        await self.product_repo.refresh(product)

        return product

    async def delete(self, product_id: int, user_id: int) -> bool:
        """Delete a product."""
        product = await self.product_repo.get_by_id(product_id, user_id)
        if not product:
            return False

        await self.product_repo.delete(product)
        await self.product_repo.commit()

        return True
