from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload
from typing import List, Dict
from datetime import datetime
from collections import defaultdict

from sales.models import Sale, SaleItem
from sales.models import SaleDeliveryStep

async def start_delivery(db: AsyncSession, sale_id: int, user_id: int) -> bool:
    """
    Start delivery process:
    1. Verify sale is closed
    2. Create SaleDeliveryStep for each unique customer
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
            status="pending"
        )
        db.add(delivery_step)
    
    # Update sale status
    sale.status = "in_progress"
    
    await db.commit()
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
    
    # Build response
    delivery_route = []
    for step in delivery_steps:
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
            "skip_reason": step.skip_reason,
            "total_amount": customer_totals[step.customer_id],
            "items": customer_items[step.customer_id]
        })

    return delivery_route

async def update_delivery_route(
    db: AsyncSession, 
    sale_id: int, 
    route: List[Dict], 
    user_id: int
) -> bool:
    """Update sequence order using offset to avoid conflicts"""
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
    return True


async def complete_delivery(
    db: AsyncSession,
    sale_id: int,
    customer_id: int,
    amount_collected: float,
    user_id: int
) -> bool:
    """Mark a delivery step as completed"""
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
            status="completed",
            is_next=False,
            completed_at=datetime.now(),
            amount_collected=amount_collected
        )
        .returning(SaleDeliveryStep)
    )
    
    updated = result.scalar_one_or_none()
    if not updated:
        raise ValueError("Delivery step not found or already completed/skipped")
    
    await db.commit()
    
    # Check if all deliveries are done
    await check_and_complete_sale(db, sale_id)
    
    return True


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
    
    return True


async def reset_delivery_to_pending(
    db: AsyncSession,
    sale_id: int,
    customer_id: int,
    user_id: int
) -> bool:
    """Reset a delivery step back to pending (undo complete/skip)"""
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
            SaleDeliveryStep.customer_id == customer_id
        )
        .values(
            status="pending",
            is_next=False,
            completed_at=None,
            amount_collected=None,
            skip_reason=None
        )
        .returning(SaleDeliveryStep)
    )
    
    updated = result.scalar_one_or_none()
    if not updated:
        raise ValueError("Delivery step not found")
    
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
        "total_expected": total_expected,
        "total_skipped_amount": total_skipped_amount,
        "current_delivery": current_delivery,
        "pending_deliveries": pending
    }
