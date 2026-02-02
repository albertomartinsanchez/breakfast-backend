import pytest
from unittest.mock import AsyncMock, MagicMock

from sales.repository import SaleRepository, SaleItemRepository
from sales.models import Sale, SaleItem


class TestSaleRepository:
    """Unit tests for SaleRepository."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock AsyncSession."""
        db = AsyncMock()
        db.add = MagicMock()
        db.delete = AsyncMock()
        db.commit = AsyncMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def repository(self, mock_db):
        """Create a SaleRepository with mocked db."""
        return SaleRepository(mock_db)

    @pytest.fixture
    def sample_sale(self):
        """Create a sample sale for testing."""
        sale = MagicMock(spec=Sale)
        sale.id = 1
        sale.user_id = 1
        sale.date = "2024-01-15"
        sale.status = "draft"
        sale.items = []
        return sale

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repository, mock_db, sample_sale):
        """Test get_by_id returns sale when found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_sale
        mock_db.execute.return_value = mock_result

        result = await repository.get_by_id(1, user_id=1)

        assert result == sample_sale
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, mock_db):
        """Test get_by_id returns None when sale not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repository.get_by_id(999, user_id=1)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_wrong_user(self, repository, mock_db):
        """Test get_by_id returns None when user_id doesn't match."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repository.get_by_id(1, user_id=999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_returns_sales(self, repository, mock_db, sample_sale):
        """Test get_all returns list of sales."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_sale]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await repository.get_all(user_id=1)

        assert len(result) == 1
        assert result[0] == sample_sale

    @pytest.mark.asyncio
    async def test_get_all_empty(self, repository, mock_db):
        """Test get_all returns empty list when no sales."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await repository.get_all(user_id=1)

        assert result == []

    @pytest.mark.asyncio
    async def test_add_sale(self, repository, mock_db, sample_sale):
        """Test add adds sale to session."""
        result = await repository.add(sample_sale)

        assert result == sample_sale
        mock_db.add.assert_called_once_with(sample_sale)

    @pytest.mark.asyncio
    async def test_update_sale(self, repository, sample_sale):
        """Test update returns the entity (SQLAlchemy tracks changes)."""
        result = await repository.update(sample_sale)

        assert result == sample_sale

    @pytest.mark.asyncio
    async def test_delete_sale(self, repository, mock_db, sample_sale):
        """Test delete removes sale from session."""
        result = await repository.delete(sample_sale)

        assert result is True
        mock_db.delete.assert_called_once_with(sample_sale)

    @pytest.mark.asyncio
    async def test_commit(self, repository, mock_db):
        """Test commit calls db.commit."""
        await repository.commit()

        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_flush(self, repository, mock_db):
        """Test flush calls db.flush."""
        await repository.flush()

        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_refetch_with_relations(self, repository, mock_db, sample_sale):
        """Test refetch_with_relations returns sale with loaded relations."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = sample_sale
        mock_db.execute.return_value = mock_result

        result = await repository.refetch_with_relations(1)

        assert result == sample_sale
        mock_db.execute.assert_called_once()


class TestSaleItemRepository:
    """Unit tests for SaleItemRepository."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock AsyncSession."""
        db = AsyncMock()
        db.add = MagicMock()
        db.delete = AsyncMock()
        return db

    @pytest.fixture
    def repository(self, mock_db):
        """Create a SaleItemRepository with mocked db."""
        return SaleItemRepository(mock_db)

    @pytest.fixture
    def sample_item(self):
        """Create a sample sale item for testing."""
        item = MagicMock(spec=SaleItem)
        item.id = 1
        item.sale_id = 1
        item.customer_id = 1
        item.product_id = 1
        item.quantity = 5
        item.buy_price_at_sale = 10.0
        item.sell_price_at_sale = 15.0
        return item

    @pytest.mark.asyncio
    async def test_add_item(self, repository, mock_db, sample_item):
        """Test add adds sale item to session."""
        result = await repository.add(sample_item)

        assert result == sample_item
        mock_db.add.assert_called_once_with(sample_item)

    @pytest.mark.asyncio
    async def test_delete_item(self, repository, mock_db, sample_item):
        """Test delete removes sale item from session."""
        result = await repository.delete(sample_item)

        assert result is True
        mock_db.delete.assert_called_once_with(sample_item)

    @pytest.mark.asyncio
    async def test_get_all_returns_empty(self, repository):
        """Test get_all returns empty list (not typically used for items)."""
        result = await repository.get_all(user_id=1)

        assert result == []
