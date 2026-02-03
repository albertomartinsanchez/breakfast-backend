import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from sales.delivery_repository import (
    DeliveryStepRepository,
    SaleDeliveryRepository,
    CustomerDeliveryRepository
)
from sales.models import Sale, SaleItem, SaleDeliveryStep
from customers.models import Customer


class TestDeliveryStepRepository:
    """Tests for DeliveryStepRepository."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.add = MagicMock()
        db.delete = AsyncMock()
        db.commit = AsyncMock()
        db.flush = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def repository(self, mock_db):
        return DeliveryStepRepository(mock_db)

    @pytest.fixture
    def sample_step(self):
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
        step.customer = MagicMock()
        step.customer.name = "John Doe"
        return step

    async def test_get_by_id_found(self, repository, mock_db, sample_step):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_step
        mock_db.execute.return_value = mock_result

        result = await repository.get_by_id(1)

        assert result == sample_step
        mock_db.execute.assert_called_once()

    async def test_get_by_id_not_found(self, repository, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repository.get_by_id(999)

        assert result is None

    async def test_get_by_sale_id(self, repository, mock_db, sample_step):
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_step]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await repository.get_by_sale_id(10)

        assert len(result) == 1
        assert result[0] == sample_step

    async def test_get_by_sale_id_empty(self, repository, mock_db):
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await repository.get_by_sale_id(10)

        assert result == []

    async def test_get_by_sale_and_customer(self, repository, mock_db, sample_step):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_step
        mock_db.execute.return_value = mock_result

        result = await repository.get_by_sale_and_customer(10, 100)

        assert result == sample_step

    async def test_get_pending_by_sale_and_customer(self, repository, mock_db, sample_step):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_step
        mock_db.execute.return_value = mock_result

        result = await repository.get_pending_by_sale_and_customer(10, 100)

        assert result == sample_step

    async def test_get_pending_by_sale(self, repository, mock_db, sample_step):
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_step]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await repository.get_pending_by_sale(10)

        assert len(result) == 1

    async def test_add(self, repository, mock_db, sample_step):
        result = await repository.add(sample_step)

        assert result == sample_step
        mock_db.add.assert_called_once_with(sample_step)

    async def test_delete(self, repository, mock_db, sample_step):
        result = await repository.delete(sample_step)

        assert result is True
        mock_db.delete.assert_called_once_with(sample_step)

    async def test_clear_is_next_for_sale(self, repository, mock_db):
        await repository.clear_is_next_for_sale(10)

        mock_db.execute.assert_called_once()

    async def test_set_is_next(self, repository, mock_db):
        await repository.set_is_next(10, 100)

        mock_db.execute.assert_called_once()

    async def test_get_max_sequence(self, repository, mock_db):
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_db.execute.return_value = mock_result

        result = await repository.get_max_sequence(10)

        assert result == 5

    async def test_get_max_sequence_none(self, repository, mock_db):
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repository.get_max_sequence(10)

        assert result == 0

    async def test_offset_all_sequences(self, repository, mock_db):
        await repository.offset_all_sequences(10, 1000)

        mock_db.execute.assert_called_once()

    async def test_update_sequence(self, repository, mock_db):
        await repository.update_sequence(10, 100, 3)

        mock_db.execute.assert_called_once()

    async def test_commit(self, repository, mock_db):
        await repository.commit()

        mock_db.commit.assert_called_once()

    async def test_flush(self, repository, mock_db):
        await repository.flush()

        mock_db.flush.assert_called_once()


class TestSaleDeliveryRepository:
    """Tests for SaleDeliveryRepository."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.flush = AsyncMock()
        return db

    @pytest.fixture
    def repository(self, mock_db):
        return SaleDeliveryRepository(mock_db)

    @pytest.fixture
    def sample_sale(self):
        sale = MagicMock(spec=Sale)
        sale.id = 10
        sale.user_id = 1
        sale.status = "closed"
        sale.items = []
        return sale

    async def test_get_sale_for_delivery(self, repository, mock_db, sample_sale):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_sale
        mock_db.execute.return_value = mock_result

        result = await repository.get_sale_for_delivery(10, 1, status="closed")

        assert result == sample_sale

    async def test_get_sale_for_delivery_not_found(self, repository, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repository.get_sale_for_delivery(999, 1)

        assert result is None

    async def test_get_sale_by_id(self, repository, mock_db, sample_sale):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_sale
        mock_db.execute.return_value = mock_result

        result = await repository.get_sale_by_id(10, 1)

        assert result == sample_sale

    async def test_update_sale_status(self, repository, mock_db):
        await repository.update_sale_status(10, "in_progress")

        mock_db.execute.assert_called_once()

    async def test_update_sale_status_if_matches(self, repository, mock_db):
        await repository.update_sale_status_if_matches(10, "completed", "in_progress")

        mock_db.execute.assert_called_once()

    async def test_get_sale_items_by_customer(self, repository, mock_db):
        item = MagicMock(spec=SaleItem)
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [item]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await repository.get_sale_items_by_customer(10, 100)

        assert len(result) == 1

    async def test_get_sale_items_with_products(self, repository, mock_db):
        item = MagicMock(spec=SaleItem)
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [item]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await repository.get_sale_items_with_products(10)

        assert len(result) == 1

    async def test_commit(self, repository, mock_db):
        await repository.commit()

        mock_db.commit.assert_called_once()

    async def test_flush(self, repository, mock_db):
        await repository.flush()

        mock_db.flush.assert_called_once()


class TestCustomerDeliveryRepository:
    """Tests for CustomerDeliveryRepository."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def repository(self, mock_db):
        return CustomerDeliveryRepository(mock_db)

    @pytest.fixture
    def sample_customer(self):
        customer = MagicMock(spec=Customer)
        customer.id = 100
        customer.name = "John Doe"
        customer.credit = 10.0
        return customer

    async def test_get_by_id(self, repository, mock_db, sample_customer):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_customer
        mock_db.execute.return_value = mock_result

        result = await repository.get_by_id(100)

        assert result == sample_customer

    async def test_get_by_id_not_found(self, repository, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repository.get_by_id(999)

        assert result is None

    async def test_get_by_ids(self, repository, mock_db, sample_customer):
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_customer]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await repository.get_by_ids([100])

        assert len(result) == 1
        assert result[0] == sample_customer

    async def test_get_by_ids_empty(self, repository, mock_db):
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await repository.get_by_ids([])

        assert result == []
