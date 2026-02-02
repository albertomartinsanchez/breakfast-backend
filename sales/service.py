from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from sales.models import Sale, SaleItem
from sales.repository import SaleRepository, SaleItemRepository
from sales.schemas import SaleCreate, SaleUpdate
from products.service import ProductService
from customers.service import CustomerService


class SaleService:
    """
    Service layer for Sale business logic.

    This class orchestrates operations using repositories and contains
    all business logic such as validation, price calculations, etc.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.sale_repo = SaleRepository(db)
        self.sale_item_repo = SaleItemRepository(db)
        self.product_service = ProductService(db)
        self.customer_service = CustomerService(db)

    async def get_all(self, user_id: int) -> List[Sale]:
        """Get all sales for a user."""
        return await self.sale_repo.get_all(user_id)

    async def get_by_id(self, sale_id: int, user_id: int) -> Optional[Sale]:
        """Get a sale by ID."""
        return await self.sale_repo.get_by_id(sale_id, user_id)

    async def create(self, sale_in: SaleCreate, user_id: int) -> Sale:
        """
        Create a new sale with items.

        Business logic:
        - Validate all customers exist
        - Validate all products exist
        - Capture current buy/sell prices at time of sale
        """
        # Validate customers and products exist
        await self._validate_sale_data(sale_in, user_id)

        # Create sale
        sale = Sale(user_id=user_id, date=sale_in.date)
        await self.sale_repo.add(sale)
        await self.sale_repo.flush()

        # Create sale items with captured prices
        for cs in sale_in.customer_sales:
            for p in cs.products:
                product = await self.product_service.get_by_id(p.product_id, user_id)
                sale_item = SaleItem(
                    sale_id=sale.id,
                    customer_id=cs.customer_id,
                    product_id=p.product_id,
                    quantity=p.quantity,
                    buy_price_at_sale=product.buy_price,
                    sell_price_at_sale=product.sell_price
                )
                await self.sale_item_repo.add(sale_item)

        await self.sale_repo.commit()

        # Re-fetch with eager loading
        return await self.sale_repo.refetch_with_relations(sale.id)

    async def update(
        self, sale_id: int, sale_in: SaleUpdate, user_id: int
    ) -> Optional[Sale]:
        """
        Update an existing sale.

        Business logic:
        - Validate all customers exist
        - Validate all products exist
        - Replace all sale items with new ones
        - Capture current buy/sell prices at time of update
        """
        sale = await self.sale_repo.get_by_id(sale_id, user_id)
        if not sale:
            return None

        # Validate customers and products exist
        await self._validate_sale_data(sale_in, user_id)

        # Update sale date
        sale.date = sale_in.date

        # Delete existing items
        for item in sale.items:
            await self.sale_item_repo.delete(item)

        # Create new sale items with captured prices
        for cs in sale_in.customer_sales:
            for p in cs.products:
                product = await self.product_service.get_by_id(p.product_id, user_id)
                sale_item = SaleItem(
                    sale_id=sale.id,
                    customer_id=cs.customer_id,
                    product_id=p.product_id,
                    quantity=p.quantity,
                    buy_price_at_sale=product.buy_price,
                    sell_price_at_sale=product.sell_price
                )
                await self.sale_item_repo.add(sale_item)

        await self.sale_repo.commit()

        # Re-fetch with eager loading
        return await self.sale_repo.refetch_with_relations(sale.id)

    async def delete(self, sale_id: int, user_id: int) -> bool:
        """Delete a sale."""
        sale = await self.sale_repo.get_by_id(sale_id, user_id)
        if not sale:
            return False

        await self.sale_repo.delete(sale)
        await self.sale_repo.commit()

        return True

    async def _validate_sale_data(self, sale_data: SaleCreate | SaleUpdate, user_id: int) -> None:
        """
        Validate that all customers and products in the sale data exist.

        Raises:
            ValueError: If any customer or product is not found
        """
        for cs in sale_data.customer_sales:
            customer = await self.customer_service.get_by_id(cs.customer_id, user_id)
            if not customer:
                raise ValueError(f"Customer {cs.customer_id} not found")

            for p in cs.products:
                product = await self.product_service.get_by_id(p.product_id, user_id)
                if not product:
                    raise ValueError(f"Product {p.product_id} not found")
