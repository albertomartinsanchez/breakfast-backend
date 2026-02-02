import pytest
from unittest.mock import AsyncMock, MagicMock

from products.repository import ProductRepository
from products.models import Product


class TestProductRepository:
    """Unit tests for ProductRepository."""

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
        """Create a ProductRepository with mocked db."""
        return ProductRepository(mock_db)

    @pytest.fixture
    def sample_product(self):
        """Create a sample product for testing."""
        product = MagicMock(spec=Product)
        product.id = 1
        product.user_id = 1
        product.name = "Test Product"
        product.description = "A test product"
        product.buy_price = 10.0
        product.sell_price = 15.0
        return product

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repository, mock_db, sample_product):
        """Test get_by_id returns product when found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_product
        mock_db.execute.return_value = mock_result

        result = await repository.get_by_id(1, user_id=1)

        assert result == sample_product
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, mock_db):
        """Test get_by_id returns None when product not found."""
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
    async def test_get_all_returns_products(self, repository, mock_db, sample_product):
        """Test get_all returns list of products."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_product]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await repository.get_all(user_id=1)

        assert len(result) == 1
        assert result[0] == sample_product

    @pytest.mark.asyncio
    async def test_get_all_empty(self, repository, mock_db):
        """Test get_all returns empty list when no products."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await repository.get_all(user_id=1)

        assert result == []

    @pytest.mark.asyncio
    async def test_add_product(self, repository, mock_db, sample_product):
        """Test add adds product to session."""
        result = await repository.add(sample_product)

        assert result == sample_product
        mock_db.add.assert_called_once_with(sample_product)

    @pytest.mark.asyncio
    async def test_update_product(self, repository, sample_product):
        """Test update returns the entity (SQLAlchemy tracks changes)."""
        result = await repository.update(sample_product)

        assert result == sample_product

    @pytest.mark.asyncio
    async def test_delete_product(self, repository, mock_db, sample_product):
        """Test delete removes product from session."""
        result = await repository.delete(sample_product)

        assert result is True
        mock_db.delete.assert_called_once_with(sample_product)

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
    async def test_refresh(self, repository, mock_db, sample_product):
        """Test refresh calls db.refresh."""
        await repository.refresh(sample_product)

        mock_db.refresh.assert_called_once_with(sample_product)
