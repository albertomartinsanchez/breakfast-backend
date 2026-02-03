from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload
from typing import List, Optional

from core.repository import BaseRepository
from sales.models import Sale, SaleItem, SaleDeliveryStep
from customers.models import Customer


class DeliveryStepRepository(BaseRepository[SaleDeliveryStep]):
    """Repository for SaleDeliveryStep data access."""

    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def get_by_id(self, id: int, user_id: int = None) -> Optional[SaleDeliveryStep]:
        """Get a delivery step by ID."""
        result = await self.db.execute(
            select(SaleDeliveryStep)
            .where(SaleDeliveryStep.id == id)
            .options(selectinload(SaleDeliveryStep.customer))
        )
        return result.scalar_one_or_none()

    async def get_all(self, user_id: int) -> List[SaleDeliveryStep]:
        """Not typically used for delivery steps."""
        return []

    async def get_by_sale_id(self, sale_id: int) -> List[SaleDeliveryStep]:
        """Get all delivery steps for a sale ordered by sequence."""
        result = await self.db.execute(
            select(SaleDeliveryStep)
            .where(SaleDeliveryStep.sale_id == sale_id)
            .order_by(SaleDeliveryStep.sequence_order)
            .options(selectinload(SaleDeliveryStep.customer))
        )
        return list(result.scalars().all())

    async def get_by_sale_and_customer(
        self, sale_id: int, customer_id: int
    ) -> Optional[SaleDeliveryStep]:
        """Get a delivery step for a specific sale and customer."""
        result = await self.db.execute(
            select(SaleDeliveryStep).where(
                SaleDeliveryStep.sale_id == sale_id,
                SaleDeliveryStep.customer_id == customer_id
            )
        )
        return result.scalar_one_or_none()

    async def get_pending_by_sale_and_customer(
        self, sale_id: int, customer_id: int
    ) -> Optional[SaleDeliveryStep]:
        """Get a pending delivery step for a specific sale and customer."""
        result = await self.db.execute(
            select(SaleDeliveryStep).where(
                SaleDeliveryStep.sale_id == sale_id,
                SaleDeliveryStep.customer_id == customer_id,
                SaleDeliveryStep.status == "pending"
            )
        )
        return result.scalar_one_or_none()

    async def get_pending_by_sale(self, sale_id: int) -> List[SaleDeliveryStep]:
        """Get all pending delivery steps for a sale."""
        result = await self.db.execute(
            select(SaleDeliveryStep).where(
                SaleDeliveryStep.sale_id == sale_id,
                SaleDeliveryStep.status == "pending"
            )
        )
        return list(result.scalars().all())

    async def add(self, entity: SaleDeliveryStep) -> SaleDeliveryStep:
        """Add a delivery step to the session."""
        self.db.add(entity)
        return entity

    async def update(self, entity: SaleDeliveryStep) -> SaleDeliveryStep:
        """Update is handled by SQLAlchemy tracking."""
        return entity

    async def delete(self, entity: SaleDeliveryStep) -> bool:
        """Delete a delivery step."""
        await self.db.delete(entity)
        return True

    async def clear_is_next_for_sale(self, sale_id: int) -> None:
        """Clear is_next flag on all delivery steps for a sale."""
        await self.db.execute(
            update(SaleDeliveryStep)
            .where(SaleDeliveryStep.sale_id == sale_id)
            .values(is_next=False)
        )

    async def set_is_next(self, sale_id: int, customer_id: int) -> None:
        """Set is_next flag for a specific customer's delivery step."""
        await self.db.execute(
            update(SaleDeliveryStep)
            .where(
                SaleDeliveryStep.sale_id == sale_id,
                SaleDeliveryStep.customer_id == customer_id
            )
            .values(is_next=True)
        )

    async def get_max_sequence(self, sale_id: int) -> int:
        """Get the maximum sequence order for a sale."""
        result = await self.db.execute(
            select(func.max(SaleDeliveryStep.sequence_order))
            .where(SaleDeliveryStep.sale_id == sale_id)
        )
        return result.scalar() or 0

    async def offset_all_sequences(self, sale_id: int, offset: int) -> None:
        """Add offset to all sequence orders for a sale."""
        await self.db.execute(
            update(SaleDeliveryStep)
            .where(SaleDeliveryStep.sale_id == sale_id)
            .values(sequence_order=SaleDeliveryStep.sequence_order + offset)
        )

    async def update_sequence(self, sale_id: int, customer_id: int, sequence: int) -> None:
        """Update sequence order for a specific delivery step."""
        await self.db.execute(
            update(SaleDeliveryStep)
            .where(
                SaleDeliveryStep.sale_id == sale_id,
                SaleDeliveryStep.customer_id == customer_id
            )
            .values(sequence_order=sequence)
        )


class SaleDeliveryRepository:
    """Repository for Sale-related delivery queries."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_sale_for_delivery(
        self, sale_id: int, user_id: int, status: str = None
    ) -> Optional[Sale]:
        """Get a sale with items and customers for delivery operations."""
        query = select(Sale).where(Sale.id == sale_id, Sale.user_id == user_id)
        if status:
            query = query.where(Sale.status == status)
        query = query.options(
            selectinload(Sale.items).selectinload(SaleItem.customer)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_sale_by_id(self, sale_id: int, user_id: int) -> Optional[Sale]:
        """Get a sale by ID for a specific user."""
        result = await self.db.execute(
            select(Sale).where(Sale.id == sale_id, Sale.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def update_sale_status(self, sale_id: int, status: str) -> None:
        """Update sale status."""
        await self.db.execute(
            update(Sale)
            .where(Sale.id == sale_id)
            .values(status=status)
        )

    async def update_sale_status_if_matches(
        self, sale_id: int, current_status: str, new_status: str
    ) -> None:
        """Update sale status only if it matches current status."""
        await self.db.execute(
            update(Sale)
            .where(Sale.id == sale_id, Sale.status == current_status)
            .values(status=new_status)
        )

    async def get_sale_items_by_customer(
        self, sale_id: int, customer_id: int
    ) -> List[SaleItem]:
        """Get all sale items for a specific customer."""
        result = await self.db.execute(
            select(SaleItem).where(
                SaleItem.sale_id == sale_id,
                SaleItem.customer_id == customer_id
            )
        )
        return list(result.scalars().all())

    async def get_sale_items_with_products(self, sale_id: int) -> List[SaleItem]:
        """Get all sale items with product and customer info."""
        result = await self.db.execute(
            select(SaleItem)
            .where(SaleItem.sale_id == sale_id)
            .options(
                selectinload(SaleItem.product),
                selectinload(SaleItem.customer)
            )
        )
        return list(result.scalars().all())

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.db.commit()

    async def flush(self) -> None:
        """Flush pending changes."""
        await self.db.flush()


class CustomerDeliveryRepository:
    """Repository for Customer-related delivery queries."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, customer_id: int) -> Optional[Customer]:
        """Get a customer by ID."""
        result = await self.db.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        return result.scalar_one_or_none()

    async def get_by_ids(self, customer_ids: List[int]) -> List[Customer]:
        """Get customers by IDs."""
        result = await self.db.execute(
            select(Customer).where(Customer.id.in_(customer_ids))
        )
        return list(result.scalars().all())
