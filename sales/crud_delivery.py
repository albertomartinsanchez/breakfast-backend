from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload
from typing import List, Dict
from datetime import datetime
from collections import defaultdict
import asyncio

from sales.models import Sale, SaleItem
from sales.models import SaleDeliveryStep
from customers.models import Customer
from notifications.events import (
    notify_delivery_started,
    notify_you_are_next,
    notify_delivery_completed,
    notify_delivery_skipped
)

async def start_delivery(db: AsyncSession, sale_id: int, user_id: int) -> bool:
    """
    Start delivery process:
    1. Verify sale is closed
    2. Create SaleDeliveryStep for each unique customer (if not already created via route setting)
    3. Set initial sequence order (alphabetical by customer name)
    4. Change sale status to in_progress
    """
    # Get sale with items
    result = await db.execute(
        select(Sale)
        .where(Sale.id == sale_id, Sale.user_id == user_id, Sale.status == "closed")
        .options(
            selectinload(Sale.items).selectinload(SaleItem.customer)
        )
    )
    sale = result.scalar_one_or_none()

    if not sale:
        raise ValueError("Sale not found or not in 'closed' status")

    # Check if delivery steps already exist (created when setting route)
    existing_result = await db.execute(
        select(SaleDeliveryStep).where(SaleDeliveryStep.sale_id == sale_id)
    )
    existing_steps = existing_result.scalars().all()

    if existing_steps:
        # Steps already exist, just update sale status and mark first as next
        sale.status = "in_progress"

        # Mark the first customer (lowest sequence_order) as is_next
        first_step = min(existing_steps, key=lambda s: s.sequence_order)
        first_step.is_next = True

        await db.commit()

        # Send push notifications to all customers
        customer_ids = [step.customer_id for step in existing_steps]
        asyncio.create_task(notify_delivery_started(db, sale_id, customer_ids))
        return True

    # No steps exist, create them with default order (alphabetical)
    # Get unique customers from sale items, sorted by name
    customer_map = {}
    for item in sale.items:
        if item.customer_id not in customer_map:
            customer_map[item.customer_id] = item.customer.name

    # Sort customers alphabetically by name
    sorted_customers = sorted(customer_map.items(), key=lambda x: x[1])

    # Create delivery steps
    for sequence, (customer_id, _) in enumerate(sorted_customers, start=1):
        delivery_step = SaleDeliveryStep(
            sale_id=sale_id,
            customer_id=customer_id,
            sequence_order=sequence,
            status="pending",
            is_next=(sequence == 1)  # First customer is marked as next
        )
        db.add(delivery_step)

    # Update sale status
    sale.status = "in_progress"

    await db.commit()

    # Send push notifications to all customers (fire and forget)
    customer_ids = [cid for cid, _ in sorted_customers]
    asyncio.create_task(notify_delivery_started(db, sale_id, customer_ids))

    return True


async def get_delivery_route(db: AsyncSession, sale_id: int, user_id: int) -> List[Dict]:
    """Get all delivery steps for a sale with customer and item details"""
    # Verify sale belongs to user
    sale_result = await db.execute(
        select(Sale).where(Sale.id == sale_id, Sale.user_id == user_id)
    )
    sale = sale_result.scalar_one_or_none()
    if not sale:
        raise ValueError("Sale not found")
    
    # Get delivery steps with customers
    result = await db.execute(
        select(SaleDeliveryStep)
        .where(SaleDeliveryStep.sale_id == sale_id)
        .order_by(SaleDeliveryStep.sequence_order)
        .options(selectinload(SaleDeliveryStep.customer))
    )
    delivery_steps = result.scalars().all()
    
    # Get sale items grouped by customer
    items_result = await db.execute(
        select(SaleItem)
        .where(SaleItem.sale_id == sale_id)
        .options(
            selectinload(SaleItem.product),
            selectinload(SaleItem.customer)
        )
    )
    sale_items = items_result.scalars().all()
    
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
    customers_result = await db.execute(
        select(Customer).where(Customer.id.in_(customer_ids))
    )
    customer_credits = {c.id: c.credit for c in customers_result.scalars().all()}

    # Build response
    delivery_route = []
    for step in delivery_steps:
        total_amount = customer_totals[step.customer_id]
        customer_credit = customer_credits.get(step.customer_id, 0.0)

        # For pending deliveries, calculate credit to apply
        # For completed deliveries, use stored credit_applied
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
    db: AsyncSession,
    sale_id: int,
    route: List[Dict],
    user_id: int
) -> bool:
    """Update sequence order using offset to avoid conflicts, or create steps if none exist"""
    # Verify sale belongs to user and check status
    sale_result = await db.execute(
        select(Sale).where(Sale.id == sale_id, Sale.user_id == user_id)
    )
    sale = sale_result.scalar_one_or_none()

    if not sale:
        raise ValueError("Sale not found")

    # Don't allow route changes if delivery is completed
    if sale.status == "completed":
        raise ValueError("Cannot modify route for completed delivery")

    # Check if delivery steps exist
    existing_result = await db.execute(
        select(SaleDeliveryStep).where(SaleDeliveryStep.sale_id == sale_id)
    )
    existing_steps = existing_result.scalars().all()

    if not existing_steps:
        # No steps exist yet (sale is closed), create them with the provided order
        for item in route:
            delivery_step = SaleDeliveryStep(
                sale_id=sale_id,
                customer_id=item["customer_id"],
                sequence_order=item["sequence"],
                status="pending"
            )
            db.add(delivery_step)
        await db.commit()
        return True

    # Steps exist, update their order
    # Get max sequence to calculate offset
    max_seq_result = await db.execute(
        select(func.max(SaleDeliveryStep.sequence_order))
        .where(SaleDeliveryStep.sale_id == sale_id)
    )
    max_seq = max_seq_result.scalar() or 0
    offset = max_seq + 1000  # Large offset to avoid any conflicts

    # Step 1: Add offset to all sequences
    await db.execute(
        update(SaleDeliveryStep)
        .where(SaleDeliveryStep.sale_id == sale_id)
        .values(sequence_order=SaleDeliveryStep.sequence_order + offset)
    )

    await db.flush()

    # Step 2: Update to final values
    for item in route:
        await db.execute(
            update(SaleDeliveryStep)
            .where(
                SaleDeliveryStep.sale_id == sale_id,
                SaleDeliveryStep.customer_id == item["customer_id"]
            )
            .values(sequence_order=item["sequence"])
        )

    await db.commit()
    return True


async def set_next_delivery(
    db: AsyncSession,
    sale_id: int,
    customer_id: int,
    user_id: int
) -> bool:
    """Set a customer as the next delivery (clears any previous selection)"""
    # Verify sale belongs to user
    sale_result = await db.execute(
        select(Sale).where(Sale.id == sale_id, Sale.user_id == user_id)
    )
    sale = sale_result.scalar_one_or_none()
    if not sale:
        raise ValueError("Sale not found")

    if sale.status != "in_progress":
        raise ValueError("Can only select next delivery for in-progress sales")

    # Verify the customer delivery step exists and is pending
    step_result = await db.execute(
        select(SaleDeliveryStep).where(
            SaleDeliveryStep.sale_id == sale_id,
            SaleDeliveryStep.customer_id == customer_id
        )
    )
    step = step_result.scalar_one_or_none()
    if not step:
        raise ValueError("Delivery step not found for this customer")

    if step.status != "pending":
        raise ValueError("Can only select pending deliveries as next")

    # Clear is_next on all delivery steps for this sale
    await db.execute(
        update(SaleDeliveryStep)
        .where(SaleDeliveryStep.sale_id == sale_id)
        .values(is_next=False)
    )

    # Set is_next on the selected customer
    await db.execute(
        update(SaleDeliveryStep)
        .where(
            SaleDeliveryStep.sale_id == sale_id,
            SaleDeliveryStep.customer_id == customer_id
        )
        .values(is_next=True)
    )

    await db.commit()

    # Send "you're next" notification (fire and forget)
    asyncio.create_task(notify_you_are_next(db, sale_id, customer_id))

    return True


async def complete_delivery(
    db: AsyncSession,
    sale_id: int,
    customer_id: int,
    amount_collected: float,
    user_id: int
) -> Dict:
    """Mark a delivery step as completed and apply customer credit"""
    # Verify sale belongs to user
    sale_result = await db.execute(
        select(Sale).where(Sale.id == sale_id, Sale.user_id == user_id)
    )
    if not sale_result.scalar_one_or_none():
        raise ValueError("Sale not found")

    # Verify delivery step exists and is pending
    step_result = await db.execute(
        select(SaleDeliveryStep).where(
            SaleDeliveryStep.sale_id == sale_id,
            SaleDeliveryStep.customer_id == customer_id,
            SaleDeliveryStep.status == "pending"
        )
    )
    step = step_result.scalar_one_or_none()
    if not step:
        raise ValueError("Delivery step not found or already completed/skipped")

    # Calculate total order amount for this customer
    items_result = await db.execute(
        select(SaleItem).where(
            SaleItem.sale_id == sale_id,
            SaleItem.customer_id == customer_id
        )
    )
    items = items_result.scalars().all()
    total_order_amount = sum(item.sell_price_at_sale * item.quantity for item in items)

    # Get customer and apply credit
    customer_result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()

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

    await db.commit()

    # Check if all deliveries are done
    await check_and_complete_sale(db, sale_id)

    # Send delivery completed notification (fire and forget)
    asyncio.create_task(notify_delivery_completed(
        db, sale_id, customer_id, amount_collected, credit_applied
    ))

    return {
        "success": True,
        "total_order_amount": total_order_amount,
        "credit_applied": credit_applied,
        "amount_collected": amount_collected,
        "new_customer_credit": customer.credit if customer else 0.0
    }


async def skip_delivery(
    db: AsyncSession,
    sale_id: int,
    customer_id: int,
    reason: str,
    user_id: int
) -> bool:
    """Skip a delivery step"""
    # Verify sale belongs to user
    sale_result = await db.execute(
        select(Sale).where(Sale.id == sale_id, Sale.user_id == user_id)
    )
    if not sale_result.scalar_one_or_none():
        raise ValueError("Sale not found")
    
    # Update delivery step
    result = await db.execute(
        update(SaleDeliveryStep)
        .where(
            SaleDeliveryStep.sale_id == sale_id,
            SaleDeliveryStep.customer_id == customer_id,
            SaleDeliveryStep.status == "pending"
        )
        .values(
            status="skipped",
            is_next=False,
            skip_reason=reason
        )
        .returning(SaleDeliveryStep)
    )
    
    updated = result.scalar_one_or_none()
    if not updated:
        raise ValueError("Delivery step not found or already completed/skipped")

    await db.commit()

    # Check if all deliveries are done
    await check_and_complete_sale(db, sale_id)

    # Send delivery skipped notification (fire and forget)
    asyncio.create_task(notify_delivery_skipped(db, sale_id, customer_id, reason))

    return True


async def reset_delivery_to_pending(
    db: AsyncSession,
    sale_id: int,
    customer_id: int,
    user_id: int
) -> bool:
    """Reset a delivery step back to pending (undo complete/skip) and restore credit if applicable"""
    # Verify sale belongs to user
    sale_result = await db.execute(
        select(Sale).where(Sale.id == sale_id, Sale.user_id == user_id)
    )
    if not sale_result.scalar_one_or_none():
        raise ValueError("Sale not found")

    # Get the delivery step to check if credit was applied
    step_result = await db.execute(
        select(SaleDeliveryStep).where(
            SaleDeliveryStep.sale_id == sale_id,
            SaleDeliveryStep.customer_id == customer_id
        )
    )
    step = step_result.scalar_one_or_none()
    if not step:
        raise ValueError("Delivery step not found")

    # If it was completed with credit applied, restore the credit
    if step.status == "completed" and step.credit_applied and step.credit_applied > 0:
        customer_result = await db.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = customer_result.scalar_one_or_none()
        if customer:
            customer.credit += step.credit_applied

    # Reset delivery step
    step.status = "pending"
    step.is_next = False
    step.completed_at = None
    step.amount_collected = None
    step.credit_applied = None
    step.skip_reason = None

    await db.commit()

    # If sale was completed, set it back to in_progress
    await db.execute(
        update(Sale)
        .where(Sale.id == sale_id, Sale.status == "completed")
        .values(status="in_progress")
    )
    await db.commit()

    return True


async def check_and_complete_sale(db: AsyncSession, sale_id: int):
    """Check if all deliveries are done and mark sale as completed"""
    result = await db.execute(
        select(SaleDeliveryStep)
        .where(
            SaleDeliveryStep.sale_id == sale_id,
            SaleDeliveryStep.status == "pending"
        )
    )
    pending = result.scalars().all()
    
    # If no pending deliveries, mark sale as completed
    if not pending:
        await db.execute(
            update(Sale)
            .where(Sale.id == sale_id)
            .values(status="completed")
        )
        await db.commit()


async def get_delivery_progress(db: AsyncSession, sale_id: int, user_id: int) -> Dict:
    """Get delivery progress statistics"""
    # Verify sale belongs to user
    sale_result = await db.execute(
        select(Sale).where(Sale.id == sale_id, Sale.user_id == user_id)
    )
    if not sale_result.scalar_one_or_none():
        raise ValueError("Sale not found")
    
    # Get all delivery steps
    delivery_route = await get_delivery_route(db, sale_id, user_id)
    
    total_deliveries = len(delivery_route)
    completed = [d for d in delivery_route if d["status"] == "completed"]
    pending = [d for d in delivery_route if d["status"] == "pending"]
    skipped = [d for d in delivery_route if d["status"] == "skipped"]
    
    total_collected = sum(d["amount_collected"] or 0 for d in completed)
    total_credit_applied = sum(d["credit_applied"] or 0 for d in completed)
    total_expected = sum(d["total_amount"] for d in delivery_route)
    total_skipped_amount = sum(d["total_amount"] for d in skipped)

    # Get current delivery (the one with is_next=True)
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
