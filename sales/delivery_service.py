from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict
from datetime import datetime
from collections import defaultdict
import asyncio

from sales.models import SaleDeliveryStep
from sales.delivery_repository import (
    DeliveryStepRepository,
    SaleDeliveryRepository,
    CustomerDeliveryRepository
)
from notifications.events import (
    notify_delivery_started,
    notify_you_are_next,
    notify_delivery_completed,
    notify_delivery_skipped
)


class DeliveryService:
    """Service for delivery business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.step_repo = DeliveryStepRepository(db)
        self.sale_repo = SaleDeliveryRepository(db)
        self.customer_repo = CustomerDeliveryRepository(db)

    async def start_delivery(self, sale_id: int, user_id: int) -> bool:
        """
        Start delivery process:
        1. Verify sale is closed
        2. Create SaleDeliveryStep for each unique customer (if not already created)
        3. Set initial sequence order (alphabetical by customer name)
        4. Change sale status to in_progress
        """
        sale = await self.sale_repo.get_sale_for_delivery(sale_id, user_id, status="closed")
        if not sale:
            raise ValueError("Sale not found or not in 'closed' status")

        existing_steps = await self.step_repo.get_by_sale_id(sale_id)

        if existing_steps:
            # Steps already exist, just update sale status and mark first as next
            sale.status = "in_progress"

            first_step = min(existing_steps, key=lambda s: s.sequence_order)
            first_step.is_next = True

            await self.step_repo.commit()

            customer_ids = [step.customer_id for step in existing_steps]
            asyncio.create_task(notify_delivery_started(self.db, sale_id, customer_ids))
            return True

        # No steps exist, create them with default order (alphabetical)
        customer_map = {}
        for item in sale.items:
            if item.customer_id not in customer_map:
                customer_map[item.customer_id] = item.customer.name

        sorted_customers = sorted(customer_map.items(), key=lambda x: x[1])

        for sequence, (customer_id, _) in enumerate(sorted_customers, start=1):
            delivery_step = SaleDeliveryStep(
                sale_id=sale_id,
                customer_id=customer_id,
                sequence_order=sequence,
                status="pending",
                is_next=(sequence == 1)
            )
            await self.step_repo.add(delivery_step)

        sale.status = "in_progress"
        await self.step_repo.commit()

        customer_ids = [cid for cid, _ in sorted_customers]
        asyncio.create_task(notify_delivery_started(self.db, sale_id, customer_ids))

        return True

    async def get_delivery_route(self, sale_id: int, user_id: int) -> List[Dict]:
        """Get all delivery steps for a sale with customer and item details."""
        sale = await self.sale_repo.get_sale_by_id(sale_id, user_id)
        if not sale:
            raise ValueError("Sale not found")

        delivery_steps = await self.step_repo.get_by_sale_id(sale_id)
        sale_items = await self.sale_repo.get_sale_items_with_products(sale_id)

        # Group items by customer
        customer_items = defaultdict(list)
        customer_totals = defaultdict(float)

        for item in sale_items:
            item_dict = {
                "product_id": item.product_id,
                "product_name": item.product.name,
                "quantity": item.quantity,
                "sell_price_at_sale": item.sell_price_at_sale,
                "total": item.sell_price_at_sale * item.quantity
            }
            customer_items[item.customer_id].append(item_dict)
            customer_totals[item.customer_id] += item_dict["total"]

        # Get customer credits
        customer_ids = list(customer_totals.keys())
        customers = await self.customer_repo.get_by_ids(customer_ids)
        customer_credits = {c.id: c.credit for c in customers}

        # Build response
        delivery_route = []
        for step in delivery_steps:
            total_amount = customer_totals[step.customer_id]
            customer_credit = customer_credits.get(step.customer_id, 0.0)

            if step.status == "pending":
                credit_to_apply = min(customer_credit, total_amount)
                amount_to_collect = total_amount - credit_to_apply
            else:
                credit_to_apply = step.credit_applied or 0.0
                amount_to_collect = step.amount_collected or 0.0

            delivery_route.append({
                "id": step.id,
                "sale_id": step.sale_id,
                "customer_id": step.customer_id,
                "customer_name": step.customer.name,
                "sequence_order": step.sequence_order,
                "status": step.status,
                "is_next": step.is_next,
                "completed_at": step.completed_at,
                "amount_collected": step.amount_collected,
                "credit_applied": step.credit_applied,
                "skip_reason": step.skip_reason,
                "total_amount": total_amount,
                "customer_credit": customer_credit,
                "credit_to_apply": credit_to_apply,
                "amount_to_collect": amount_to_collect,
                "items": customer_items[step.customer_id]
            })

        return delivery_route

    async def update_delivery_route(
        self, sale_id: int, route: List[Dict], user_id: int
    ) -> bool:
        """Update sequence order or create steps if none exist."""
        sale = await self.sale_repo.get_sale_by_id(sale_id, user_id)
        if not sale:
            raise ValueError("Sale not found")

        if sale.status == "completed":
            raise ValueError("Cannot modify route for completed delivery")

        existing_steps = await self.step_repo.get_by_sale_id(sale_id)

        if not existing_steps:
            # Create new steps with provided order
            for item in route:
                delivery_step = SaleDeliveryStep(
                    sale_id=sale_id,
                    customer_id=item["customer_id"],
                    sequence_order=item["sequence"],
                    status="pending"
                )
                await self.step_repo.add(delivery_step)
            await self.step_repo.commit()
            return True

        # Update existing steps using offset to avoid conflicts
        max_seq = await self.step_repo.get_max_sequence(sale_id)
        offset = max_seq + 1000

        await self.step_repo.offset_all_sequences(sale_id, offset)
        await self.step_repo.flush()

        for item in route:
            await self.step_repo.update_sequence(
                sale_id, item["customer_id"], item["sequence"]
            )

        await self.step_repo.commit()
        return True

    async def set_next_delivery(
        self, sale_id: int, customer_id: int, user_id: int
    ) -> bool:
        """Set a customer as the next delivery."""
        sale = await self.sale_repo.get_sale_by_id(sale_id, user_id)
        if not sale:
            raise ValueError("Sale not found")

        if sale.status != "in_progress":
            raise ValueError("Can only select next delivery for in-progress sales")

        step = await self.step_repo.get_by_sale_and_customer(sale_id, customer_id)
        if not step:
            raise ValueError("Delivery step not found for this customer")

        if step.status != "pending":
            raise ValueError("Can only select pending deliveries as next")

        await self.step_repo.clear_is_next_for_sale(sale_id)
        await self.step_repo.set_is_next(sale_id, customer_id)
        await self.step_repo.commit()

        asyncio.create_task(notify_you_are_next(self.db, sale_id, customer_id))

        return True

    async def complete_delivery(
        self, sale_id: int, customer_id: int, amount_collected: float, user_id: int
    ) -> Dict:
        """Mark a delivery step as completed and apply customer credit."""
        sale = await self.sale_repo.get_sale_by_id(sale_id, user_id)
        if not sale:
            raise ValueError("Sale not found")

        step = await self.step_repo.get_pending_by_sale_and_customer(sale_id, customer_id)
        if not step:
            raise ValueError("Delivery step not found or already completed/skipped")

        # Calculate total order amount
        items = await self.sale_repo.get_sale_items_by_customer(sale_id, customer_id)
        total_order_amount = sum(
            item.sell_price_at_sale * item.quantity for item in items
        )

        # Get customer and apply credit
        customer = await self.customer_repo.get_by_id(customer_id)

        credit_applied = 0.0
        if customer and customer.credit > 0:
            credit_applied = min(customer.credit, total_order_amount)
            customer.credit -= credit_applied

        # Update delivery step
        step.status = "completed"
        step.is_next = False
        step.completed_at = datetime.now()
        step.amount_collected = amount_collected
        step.credit_applied = credit_applied

        await self.step_repo.commit()

        # Check if all deliveries are done
        await self._check_and_complete_sale(sale_id)

        asyncio.create_task(notify_delivery_completed(
            self.db, sale_id, customer_id, amount_collected, credit_applied
        ))

        return {
            "success": True,
            "total_order_amount": total_order_amount,
            "credit_applied": credit_applied,
            "amount_collected": amount_collected,
            "new_customer_credit": customer.credit if customer else 0.0
        }

    async def skip_delivery(
        self, sale_id: int, customer_id: int, reason: str, user_id: int
    ) -> bool:
        """Skip a delivery step."""
        sale = await self.sale_repo.get_sale_by_id(sale_id, user_id)
        if not sale:
            raise ValueError("Sale not found")

        step = await self.step_repo.get_pending_by_sale_and_customer(sale_id, customer_id)
        if not step:
            raise ValueError("Delivery step not found or already completed/skipped")

        step.status = "skipped"
        step.is_next = False
        step.skip_reason = reason

        await self.step_repo.commit()

        # Check if all deliveries are done
        await self._check_and_complete_sale(sale_id)

        asyncio.create_task(notify_delivery_skipped(self.db, sale_id, customer_id, reason))

        return True

    async def reset_delivery_to_pending(
        self, sale_id: int, customer_id: int, user_id: int
    ) -> bool:
        """Reset a delivery step back to pending and restore credit if applicable."""
        sale = await self.sale_repo.get_sale_by_id(sale_id, user_id)
        if not sale:
            raise ValueError("Sale not found")

        step = await self.step_repo.get_by_sale_and_customer(sale_id, customer_id)
        if not step:
            raise ValueError("Delivery step not found")

        # Restore credit if it was applied
        if step.status == "completed" and step.credit_applied and step.credit_applied > 0:
            customer = await self.customer_repo.get_by_id(customer_id)
            if customer:
                customer.credit += step.credit_applied

        # Reset step
        step.status = "pending"
        step.is_next = False
        step.completed_at = None
        step.amount_collected = None
        step.credit_applied = None
        step.skip_reason = None

        await self.step_repo.commit()

        # If sale was completed, set it back to in_progress
        await self.sale_repo.update_sale_status_if_matches(sale_id, "completed", "in_progress")
        await self.sale_repo.commit()

        return True

    async def get_delivery_progress(self, sale_id: int, user_id: int) -> Dict:
        """Get delivery progress statistics."""
        sale = await self.sale_repo.get_sale_by_id(sale_id, user_id)
        if not sale:
            raise ValueError("Sale not found")

        delivery_route = await self.get_delivery_route(sale_id, user_id)

        total_deliveries = len(delivery_route)
        completed = [d for d in delivery_route if d["status"] == "completed"]
        pending = [d for d in delivery_route if d["status"] == "pending"]
        skipped = [d for d in delivery_route if d["status"] == "skipped"]

        total_collected = sum(d["amount_collected"] or 0 for d in completed)
        total_credit_applied = sum(d["credit_applied"] or 0 for d in completed)
        total_expected = sum(d["total_amount"] for d in delivery_route)
        total_skipped_amount = sum(d["total_amount"] for d in skipped)

        current_delivery = next((d for d in pending if d["is_next"]), None)

        return {
            "total_deliveries": total_deliveries,
            "completed_count": len(completed),
            "pending_count": len(pending),
            "skipped_count": len(skipped),
            "total_collected": total_collected,
            "total_credit_applied": total_credit_applied,
            "total_expected": total_expected,
            "total_skipped_amount": total_skipped_amount,
            "current_delivery": current_delivery,
            "pending_deliveries": pending
        }

    async def _check_and_complete_sale(self, sale_id: int) -> None:
        """Check if all deliveries are done and mark sale as completed."""
        pending = await self.step_repo.get_pending_by_sale(sale_id)

        if not pending:
            await self.sale_repo.update_sale_status(sale_id, "completed")
            await self.sale_repo.commit()
