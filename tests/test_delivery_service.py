import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from sales.delivery_service import DeliveryService
from sales.models import Sale, SaleItem, SaleDeliveryStep
from customers.models import Customer
from products.models import Product


class TestDeliveryService:
    """Tests for DeliveryService."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        return DeliveryService(mock_db)

    @pytest.fixture
    def sample_sale(self):
        sale = MagicMock(spec=Sale)
        sale.id = 10
        sale.user_id = 1
        sale.status = "closed"

        # Create customer mock
        customer = MagicMock(spec=Customer)
        customer.id = 100
        customer.name = "John Doe"
        customer.credit = 5.0

        # Create product mock
        product = MagicMock(spec=Product)
        product.id = 200
        product.name = "Bread"

        # Create sale item
        item = MagicMock(spec=SaleItem)
        item.customer_id = 100
        item.customer = customer
        item.product_id = 200
        item.product = product
        item.quantity = 2
        item.sell_price_at_sale = 3.50

        sale.items = [item]
        return sale

    @pytest.fixture
    def sample_step(self):
        customer = MagicMock()
        customer.id = 100
        customer.name = "John Doe"

        step = MagicMock(spec=SaleDeliveryStep)
        step.id = 1
        step.sale_id = 10
        step.customer_id = 100
        step.sequence_order = 1
        step.status = "pending"
        step.is_next = True
        step.completed_at = None
        step.amount_collected = None
        step.credit_applied = None
        step.skip_reason = None
        step.customer = customer
        return step

    @patch('sales.delivery_service.notify_delivery_started')
    async def test_start_delivery_creates_steps(self, mock_notify, service, sample_sale):
        service.sale_repo.get_sale_for_delivery = AsyncMock(return_value=sample_sale)
        service.step_repo.get_by_sale_id = AsyncMock(return_value=[])
        service.step_repo.add = AsyncMock()
        service.step_repo.commit = AsyncMock()

        result = await service.start_delivery(10, 1)

        assert result is True
        service.step_repo.add.assert_called_once()

    @patch('sales.delivery_service.notify_delivery_started')
    async def test_start_delivery_with_existing_steps(self, mock_notify, service, sample_sale, sample_step):
        sample_sale.status = "closed"
        service.sale_repo.get_sale_for_delivery = AsyncMock(return_value=sample_sale)
        service.step_repo.get_by_sale_id = AsyncMock(return_value=[sample_step])
        service.step_repo.commit = AsyncMock()

        result = await service.start_delivery(10, 1)

        assert result is True
        assert sample_sale.status == "in_progress"

    async def test_start_delivery_sale_not_found(self, service):
        service.sale_repo.get_sale_for_delivery = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Sale not found or not in 'closed' status"):
            await service.start_delivery(10, 1)

    async def test_get_delivery_route(self, service, sample_step):
        sale = MagicMock()
        sale.id = 10

        product = MagicMock()
        product.name = "Bread"

        customer = MagicMock()
        customer.id = 100
        customer.credit = 5.0

        item = MagicMock()
        item.customer_id = 100
        item.product_id = 200
        item.product = product
        item.quantity = 2
        item.sell_price_at_sale = 3.50

        service.sale_repo.get_sale_by_id = AsyncMock(return_value=sale)
        service.step_repo.get_by_sale_id = AsyncMock(return_value=[sample_step])
        service.sale_repo.get_sale_items_with_products = AsyncMock(return_value=[item])
        service.customer_repo.get_by_ids = AsyncMock(return_value=[customer])

        result = await service.get_delivery_route(10, 1)

        assert len(result) == 1
        assert result[0]["customer_id"] == 100
        assert result[0]["customer_name"] == "John Doe"
        assert result[0]["total_amount"] == 7.0  # 2 * 3.50

    async def test_get_delivery_route_sale_not_found(self, service):
        service.sale_repo.get_sale_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Sale not found"):
            await service.get_delivery_route(10, 1)

    async def test_update_delivery_route_creates_steps(self, service):
        sale = MagicMock()
        sale.status = "closed"

        service.sale_repo.get_sale_by_id = AsyncMock(return_value=sale)
        service.step_repo.get_by_sale_id = AsyncMock(return_value=[])
        service.step_repo.add = AsyncMock()
        service.step_repo.commit = AsyncMock()

        route = [{"customer_id": 100, "sequence": 1}]
        result = await service.update_delivery_route(10, route, 1)

        assert result is True
        service.step_repo.add.assert_called_once()

    async def test_update_delivery_route_updates_existing(self, service, sample_step):
        sale = MagicMock()
        sale.status = "in_progress"

        service.sale_repo.get_sale_by_id = AsyncMock(return_value=sale)
        service.step_repo.get_by_sale_id = AsyncMock(return_value=[sample_step])
        service.step_repo.get_max_sequence = AsyncMock(return_value=1)
        service.step_repo.offset_all_sequences = AsyncMock()
        service.step_repo.flush = AsyncMock()
        service.step_repo.update_sequence = AsyncMock()
        service.step_repo.commit = AsyncMock()

        route = [{"customer_id": 100, "sequence": 1}]
        result = await service.update_delivery_route(10, route, 1)

        assert result is True

    async def test_update_delivery_route_completed_sale(self, service):
        sale = MagicMock()
        sale.status = "completed"

        service.sale_repo.get_sale_by_id = AsyncMock(return_value=sale)

        with pytest.raises(ValueError, match="Cannot modify route for completed delivery"):
            await service.update_delivery_route(10, [], 1)

    async def test_update_delivery_route_sale_not_found(self, service):
        service.sale_repo.get_sale_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Sale not found"):
            await service.update_delivery_route(10, [], 1)

    @patch('sales.delivery_service.notify_you_are_next')
    async def test_set_next_delivery(self, mock_notify, service, sample_step):
        sale = MagicMock()
        sale.status = "in_progress"

        service.sale_repo.get_sale_by_id = AsyncMock(return_value=sale)
        service.step_repo.get_by_sale_and_customer = AsyncMock(return_value=sample_step)
        service.step_repo.clear_is_next_for_sale = AsyncMock()
        service.step_repo.set_is_next = AsyncMock()
        service.step_repo.commit = AsyncMock()

        result = await service.set_next_delivery(10, 100, 1)

        assert result is True

    async def test_set_next_delivery_sale_not_found(self, service):
        service.sale_repo.get_sale_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Sale not found"):
            await service.set_next_delivery(10, 100, 1)

    async def test_set_next_delivery_wrong_status(self, service):
        sale = MagicMock()
        sale.status = "closed"

        service.sale_repo.get_sale_by_id = AsyncMock(return_value=sale)

        with pytest.raises(ValueError, match="Can only select next delivery for in-progress sales"):
            await service.set_next_delivery(10, 100, 1)

    async def test_set_next_delivery_step_not_found(self, service):
        sale = MagicMock()
        sale.status = "in_progress"

        service.sale_repo.get_sale_by_id = AsyncMock(return_value=sale)
        service.step_repo.get_by_sale_and_customer = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Delivery step not found"):
            await service.set_next_delivery(10, 100, 1)

    async def test_set_next_delivery_not_pending(self, service, sample_step):
        sale = MagicMock()
        sale.status = "in_progress"
        sample_step.status = "completed"

        service.sale_repo.get_sale_by_id = AsyncMock(return_value=sale)
        service.step_repo.get_by_sale_and_customer = AsyncMock(return_value=sample_step)

        with pytest.raises(ValueError, match="Can only select pending deliveries"):
            await service.set_next_delivery(10, 100, 1)

    @patch('sales.delivery_service.notify_delivery_completed')
    async def test_complete_delivery(self, mock_notify, service, sample_step):
        sale = MagicMock()

        customer = MagicMock()
        customer.credit = 5.0

        item = MagicMock()
        item.sell_price_at_sale = 3.50
        item.quantity = 2

        service.sale_repo.get_sale_by_id = AsyncMock(return_value=sale)
        service.step_repo.get_pending_by_sale_and_customer = AsyncMock(return_value=sample_step)
        service.sale_repo.get_sale_items_by_customer = AsyncMock(return_value=[item])
        service.customer_repo.get_by_id = AsyncMock(return_value=customer)
        service.step_repo.commit = AsyncMock()
        service.step_repo.get_pending_by_sale = AsyncMock(return_value=[])
        service.sale_repo.update_sale_status = AsyncMock()
        service.sale_repo.commit = AsyncMock()

        result = await service.complete_delivery(10, 100, 2.0, 1)

        assert result["success"] is True
        assert result["total_order_amount"] == 7.0
        assert result["credit_applied"] == 5.0  # min(5.0, 7.0)
        assert customer.credit == 0.0

    async def test_complete_delivery_sale_not_found(self, service):
        service.sale_repo.get_sale_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Sale not found"):
            await service.complete_delivery(10, 100, 2.0, 1)

    async def test_complete_delivery_step_not_found(self, service):
        sale = MagicMock()

        service.sale_repo.get_sale_by_id = AsyncMock(return_value=sale)
        service.step_repo.get_pending_by_sale_and_customer = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Delivery step not found or already completed/skipped"):
            await service.complete_delivery(10, 100, 2.0, 1)

    @patch('sales.delivery_service.notify_delivery_skipped')
    async def test_skip_delivery(self, mock_notify, service, sample_step):
        sale = MagicMock()

        service.sale_repo.get_sale_by_id = AsyncMock(return_value=sale)
        service.step_repo.get_pending_by_sale_and_customer = AsyncMock(return_value=sample_step)
        service.step_repo.commit = AsyncMock()
        service.step_repo.get_pending_by_sale = AsyncMock(return_value=[])
        service.sale_repo.update_sale_status = AsyncMock()
        service.sale_repo.commit = AsyncMock()

        result = await service.skip_delivery(10, 100, "Not home", 1)

        assert result is True
        assert sample_step.status == "skipped"
        assert sample_step.skip_reason == "Not home"

    async def test_skip_delivery_sale_not_found(self, service):
        service.sale_repo.get_sale_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Sale not found"):
            await service.skip_delivery(10, 100, "Not home", 1)

    async def test_skip_delivery_step_not_found(self, service):
        sale = MagicMock()

        service.sale_repo.get_sale_by_id = AsyncMock(return_value=sale)
        service.step_repo.get_pending_by_sale_and_customer = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Delivery step not found or already completed/skipped"):
            await service.skip_delivery(10, 100, "Not home", 1)

    async def test_reset_delivery_to_pending(self, service, sample_step):
        sale = MagicMock()
        sample_step.status = "completed"
        sample_step.credit_applied = 5.0

        customer = MagicMock()
        customer.credit = 0.0

        service.sale_repo.get_sale_by_id = AsyncMock(return_value=sale)
        service.step_repo.get_by_sale_and_customer = AsyncMock(return_value=sample_step)
        service.customer_repo.get_by_id = AsyncMock(return_value=customer)
        service.step_repo.commit = AsyncMock()
        service.sale_repo.update_sale_status_if_matches = AsyncMock()
        service.sale_repo.commit = AsyncMock()

        result = await service.reset_delivery_to_pending(10, 100, 1)

        assert result is True
        assert sample_step.status == "pending"
        assert customer.credit == 5.0  # Credit restored

    async def test_reset_delivery_sale_not_found(self, service):
        service.sale_repo.get_sale_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Sale not found"):
            await service.reset_delivery_to_pending(10, 100, 1)

    async def test_reset_delivery_step_not_found(self, service):
        sale = MagicMock()

        service.sale_repo.get_sale_by_id = AsyncMock(return_value=sale)
        service.step_repo.get_by_sale_and_customer = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Delivery step not found"):
            await service.reset_delivery_to_pending(10, 100, 1)

    async def test_get_delivery_progress(self, service):
        sale = MagicMock()

        # Mock get_delivery_route to return a list of steps
        completed_step = {
            "status": "completed",
            "amount_collected": 5.0,
            "credit_applied": 2.0,
            "total_amount": 7.0,
            "is_next": False
        }
        pending_step = {
            "status": "pending",
            "amount_collected": None,
            "credit_applied": None,
            "total_amount": 10.0,
            "is_next": True
        }
        skipped_step = {
            "status": "skipped",
            "amount_collected": None,
            "credit_applied": None,
            "total_amount": 3.0,
            "is_next": False
        }

        service.sale_repo.get_sale_by_id = AsyncMock(return_value=sale)
        service.get_delivery_route = AsyncMock(return_value=[completed_step, pending_step, skipped_step])

        result = await service.get_delivery_progress(10, 1)

        assert result["total_deliveries"] == 3
        assert result["completed_count"] == 1
        assert result["pending_count"] == 1
        assert result["skipped_count"] == 1
        assert result["total_collected"] == 5.0
        assert result["total_credit_applied"] == 2.0
        assert result["total_expected"] == 20.0
        assert result["total_skipped_amount"] == 3.0
        assert result["current_delivery"] == pending_step

    async def test_get_delivery_progress_sale_not_found(self, service):
        service.sale_repo.get_sale_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Sale not found"):
            await service.get_delivery_progress(10, 1)

    async def test_check_and_complete_sale_no_pending(self, service):
        service.step_repo.get_pending_by_sale = AsyncMock(return_value=[])
        service.sale_repo.update_sale_status = AsyncMock()
        service.sale_repo.commit = AsyncMock()

        await service._check_and_complete_sale(10)

        service.sale_repo.update_sale_status.assert_called_once_with(10, "completed")

    async def test_check_and_complete_sale_has_pending(self, service, sample_step):
        service.step_repo.get_pending_by_sale = AsyncMock(return_value=[sample_step])
        service.sale_repo.update_sale_status = AsyncMock()

        await service._check_and_complete_sale(10)

        service.sale_repo.update_sale_status.assert_not_called()
