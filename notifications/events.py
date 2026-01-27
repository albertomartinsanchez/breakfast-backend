"""
Notification events triggered by business actions.
These functions are called from the delivery workflow to send push notifications.
"""
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from notifications.services import (
    send_to_customer,
    send_to_customers,
    NotificationType
)

logger = logging.getLogger(__name__)


async def notify_sale_open(db: AsyncSession, sale_id: int, sale_date: str, customer_ids: List[int]):
    """Notify customers that a sale is now open for orders"""
    logger.info(f"Sending sale_open notifications for sale {sale_id} to {len(customer_ids)} customers")

    result = await send_to_customers(
        db,
        customer_ids,
        title="New Sale Available!",
        body=f"A new sale for {sale_date} is now open. Place your order!",
        data={"sale_id": sale_id, "sale_date": sale_date},
        notification_type=NotificationType.SALE_OPEN
    )
    logger.info(f"Sale open notifications: {result}")
    return result


async def notify_sale_closed(db: AsyncSession, sale_id: int, customer_ids: List[int]):
    """Notify customers that a sale is now closed for orders"""
    logger.info(f"Sending sale_closed notifications for sale {sale_id}")

    result = await send_to_customers(
        db,
        customer_ids,
        title="Orders Closed",
        body="Order cutoff reached. Your order will be delivered soon!",
        data={"sale_id": sale_id},
        notification_type=NotificationType.SALE_CLOSED
    )
    logger.info(f"Sale closed notifications: {result}")
    return result


async def notify_sale_deleted(db: AsyncSession, sale_id: int, sale_date: str, customer_ids: List[int]):
    """Notify customers that a sale has been deleted/cancelled"""
    logger.info(f"Sending sale_deleted notifications for sale {sale_id} to {len(customer_ids)} customers")

    result = await send_to_customers(
        db,
        customer_ids,
        title="Sale Cancelled",
        body=f"The sale for {sale_date} has been cancelled.",
        data={"sale_id": sale_id, "sale_date": sale_date},
        notification_type=NotificationType.SALE_DELETED
    )
    logger.info(f"Sale deleted notifications: {result}")
    return result


async def notify_delivery_started(db: AsyncSession, sale_id: int, customer_ids: List[int]):
    """Notify customers that delivery has started"""
    logger.info(f"Sending delivery_started notifications for sale {sale_id}")

    result = await send_to_customers(
        db,
        customer_ids,
        title="Delivery Started!",
        body="Your delivery is on its way! Track your position in the app.",
        data={"sale_id": sale_id},
        notification_type=NotificationType.DELIVERY_STARTED
    )
    logger.info(f"Delivery started notifications: {result}")
    return result


async def notify_you_are_next(db: AsyncSession, sale_id: int, customer_id: int):
    """Notify customer they are next in the delivery queue"""
    logger.info(f"Sending you_are_next notification to customer {customer_id}")

    result = await send_to_customer(
        db,
        customer_id,
        title="You're Next!",
        body="The driver is heading to you next. Please be ready!",
        data={"sale_id": sale_id},
        notification_type=NotificationType.YOU_ARE_NEXT
    )
    logger.info(f"You are next notification: {result}")
    return result


async def notify_delivery_completed(
    db: AsyncSession,
    sale_id: int,
    customer_id: int,
    amount_collected: float,
    credit_applied: float
):
    """Notify customer their delivery is completed"""
    logger.info(f"Sending delivery_completed notification to customer {customer_id}")

    body = "Your delivery has been completed!"
    if credit_applied > 0:
        body = f"Delivery completed! Credit applied: ${credit_applied:.2f}"

    result = await send_to_customer(
        db,
        customer_id,
        title="Delivery Complete!",
        body=body,
        data={
            "sale_id": sale_id,
            "amount_collected": amount_collected,
            "credit_applied": credit_applied
        },
        notification_type=NotificationType.DELIVERY_COMPLETED
    )
    logger.info(f"Delivery completed notification: {result}")
    return result


async def notify_delivery_skipped(
    db: AsyncSession,
    sale_id: int,
    customer_id: int,
    reason: Optional[str] = None
):
    """Notify customer their delivery was skipped"""
    logger.info(f"Sending delivery_skipped notification to customer {customer_id}")

    body = "Your delivery was skipped."
    if reason:
        body = f"Your delivery was skipped: {reason}"

    result = await send_to_customer(
        db,
        customer_id,
        title="Delivery Skipped",
        body=body,
        data={"sale_id": sale_id, "reason": reason or ""},
        notification_type=NotificationType.DELIVERY_SKIPPED
    )
    logger.info(f"Delivery skipped notification: {result}")
    return result
