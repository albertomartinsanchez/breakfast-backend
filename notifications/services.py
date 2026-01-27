import logging
from typing import List, Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)

# Firebase Admin SDK - initialized lazily
_firebase_app = None


class NotificationType(str, Enum):
    SALE_OPEN = "sale_open"
    SALE_CLOSED = "sale_closed"
    SALE_DELETED = "sale_deleted"
    DELIVERY_STARTED = "delivery_started"
    YOU_ARE_NEXT = "you_are_next"
    DELIVERY_COMPLETED = "delivery_completed"
    DELIVERY_SKIPPED = "delivery_skipped"


def _get_firebase_app():
    """Lazily initialize Firebase Admin SDK"""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    try:
        import firebase_admin
        from firebase_admin import credentials
        from core.config import settings

        if hasattr(settings, 'firebase_credentials_path') and settings.firebase_credentials_path:
            cred = credentials.Certificate(settings.firebase_credentials_path)
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully")
        else:
            logger.warning("Firebase credentials not configured - push notifications disabled")
            return None
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
        return None

    return _firebase_app


async def send_push_notification(
    device_tokens: List[str],
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
    notification_type: Optional[NotificationType] = None
) -> Dict[str, Any]:
    """
    Send push notification to multiple devices via FCM.
    Returns dict with success_count, failure_count, and failed_tokens.
    """
    if not device_tokens:
        return {"success_count": 0, "failure_count": 0, "failed_tokens": []}

    app = _get_firebase_app()
    if app is None:
        logger.warning("Firebase not configured, skipping push notification")
        return {"success_count": 0, "failure_count": 0, "failed_tokens": [], "skipped": True}

    try:
        from firebase_admin import messaging

        # Build notification payload
        notification = messaging.Notification(
            title=title,
            body=body
        )

        # Add notification type to data
        message_data = data or {}
        if notification_type:
            message_data["type"] = notification_type.value

        # Android-specific config
        android_config = messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                icon="ic_notification",
                color="#FF6B35",
                channel_id="breakfast_delivery"
            )
        )

        success_count = 0
        failure_count = 0
        failed_tokens = []

        # Send to each device individually for better error tracking
        for token in device_tokens:
            try:
                message = messaging.Message(
                    notification=notification,
                    data={k: str(v) for k, v in message_data.items()},
                    android=android_config,
                    token=token
                )
                messaging.send(message)
                success_count += 1
            except messaging.UnregisteredError:
                # Token is no longer valid
                failed_tokens.append(token)
                failure_count += 1
            except Exception as e:
                logger.error(f"Failed to send to token {token[:20]}...: {e}")
                failure_count += 1

        return {
            "success_count": success_count,
            "failure_count": failure_count,
            "failed_tokens": failed_tokens
        }

    except Exception as e:
        logger.error(f"Error sending push notifications: {e}")
        return {"success_count": 0, "failure_count": len(device_tokens), "failed_tokens": []}


async def send_to_customer(
    db,
    customer_id: int,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
    notification_type: Optional[NotificationType] = None
) -> Dict[str, Any]:
    """Send notification to all devices of a specific customer"""
    from notifications.crud import get_customer_devices, deactivate_device

    devices = await get_customer_devices(db, customer_id)
    tokens = [d.device_token for d in devices]

    if not tokens:
        return {"success_count": 0, "failure_count": 0, "no_devices": True}

    result = await send_push_notification(tokens, title, body, data, notification_type)

    # Deactivate failed tokens
    for token in result.get("failed_tokens", []):
        await deactivate_device(db, token)

    return result


async def send_to_customers(
    db,
    customer_ids: List[int],
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
    notification_type: Optional[NotificationType] = None
) -> Dict[str, Any]:
    """Send notification to all devices of multiple customers"""
    from notifications.crud import get_devices_for_customers, deactivate_device

    devices = await get_devices_for_customers(db, customer_ids)
    tokens = [d.device_token for d in devices]

    if not tokens:
        return {"success_count": 0, "failure_count": 0, "no_devices": True}

    result = await send_push_notification(tokens, title, body, data, notification_type)

    # Deactivate failed tokens
    for token in result.get("failed_tokens", []):
        await deactivate_device(db, token)

    return result
