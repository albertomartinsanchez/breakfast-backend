import pytest
from unittest.mock import AsyncMock, MagicMock

from products.service import ProductService
from products.models import Product
from products.schemas import ProductCreate, ProductUpdate


class TestProductService:
    """Unit tests for ProductService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock AsyncSession."""
        return AsyncMock()

    @pytest.fixture
    def mock_product_repo(self):
        """Create a mock ProductRepository."""
        repo = AsyncMock()
        repo.get_by_id = AsyncMock()
        repo.get_all = AsyncMock()
        repo.add = AsyncMock()
        repo.update = AsyncMock()
        repo.delete = AsyncMock()
        repo.commit = AsyncMock()
        repo.flush = AsyncMock()
        repo.refresh = AsyncMock()
        return repo

    @pytest.fixture
    def service(self, mock_db, mock_product_repo):
        """Create a ProductService with mocked repository."""
        service = ProductService(mock_db)
        service.product_repo = mock_product_repo
        return service

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

    @pytest.fixture
    def product_create_data(self):
        """Create sample ProductCreate data."""
        return ProductCreate(
            name="Test Product",
            description="A test product",
            buy_price=10.0,
            sell_price=15.0
        )

    @pytest.fixture
    def product_update_data(self):
        """Create sample ProductUpdate data."""
        return ProductUpdate(
            name="Updated Product",
            description="An updated product",
            buy_price=12.0,
            sell_price=18.0
        )

    # =========================================================================
    # get_all tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_all_returns_products(self, service, mock_product_repo, sample_product):
        """Test get_all returns list of products from repository."""
        mock_product_repo.get_all.return_value = [sample_product]

        result = await service.get_all(user_id=1)

        assert len(result) == 1
        assert result[0] == sample_product
        mock_product_repo.get_all.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_all_empty(self, service, mock_product_repo):
        """Test get_all returns empty list when no products."""
        mock_product_repo.get_all.return_value = []

        result = await service.get_all(user_id=1)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_all_multiple_products(self, service, mock_product_repo):
        """Test get_all returns multiple products."""
        products = [MagicMock(spec=Product) for _ in range(3)]
        mock_product_repo.get_all.return_value = products

        result = await service.get_all(user_id=1)

        assert len(result) == 3

    # =========================================================================
    # get_by_id tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, service, mock_product_repo, sample_product):
        """Test get_by_id returns product when found."""
        mock_product_repo.get_by_id.return_value = sample_product

        result = await service.get_by_id(product_id=1, user_id=1)

        assert result == sample_product
        mock_product_repo.get_by_id.assert_called_once_with(1, 1)

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service, mock_product_repo):
        """Test get_by_id returns None when product not found."""
        mock_product_repo.get_by_id.return_value = None

        result = await service.get_by_id(product_id=999, user_id=1)

        assert result is None

    # =========================================================================
    # create tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_create_product_success(self, service, mock_product_repo, product_create_data):
        """Test create successfully creates product."""
        captured_product = None

        async def capture_add(product):
            nonlocal captured_product
            captured_product = product
            product.id = 1
            return product

        mock_product_repo.add.side_effect = capture_add

        result = await service.create(product_create_data, user_id=1)

        mock_product_repo.add.assert_called_once()
        assert captured_product is not None
        assert captured_product.name == "Test Product"
        assert captured_product.description == "A test product"
        assert captured_product.buy_price == 10.0
        assert captured_product.sell_price == 15.0
        assert captured_product.user_id == 1

        mock_product_repo.commit.assert_called_once()
        mock_product_repo.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_product_without_description(self, service, mock_product_repo):
        """Test create product without description."""
        product_data = ProductCreate(
            name="Simple Product",
            description=None,
            buy_price=5.0,
            sell_price=8.0
        )

        async def capture_add(product):
            product.id = 1
            return product

        mock_product_repo.add.side_effect = capture_add

        await service.create(product_data, user_id=1)

        added_product = mock_product_repo.add.call_args[0][0]
        assert added_product.name == "Simple Product"
        assert added_product.description is None

    # =========================================================================
    # update tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_update_product_success(self, service, mock_product_repo, sample_product, product_update_data):
        """Test update successfully updates product."""
        mock_product_repo.get_by_id.return_value = sample_product

        result = await service.update(product_id=1, product_in=product_update_data, user_id=1)

        assert result == sample_product
        assert sample_product.name == "Updated Product"
        assert sample_product.description == "An updated product"
        assert sample_product.buy_price == 12.0
        assert sample_product.sell_price == 18.0
        mock_product_repo.commit.assert_called_once()
        mock_product_repo.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_product_not_found(self, service, mock_product_repo, product_update_data):
        """Test update returns None when product not found."""
        mock_product_repo.get_by_id.return_value = None

        result = await service.update(product_id=999, product_in=product_update_data, user_id=1)

        assert result is None
        mock_product_repo.commit.assert_not_called()

    # =========================================================================
    # delete tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_delete_product_success(self, service, mock_product_repo, sample_product):
        """Test delete successfully removes product."""
        mock_product_repo.get_by_id.return_value = sample_product
        mock_product_repo.delete.return_value = True

        result = await service.delete(product_id=1, user_id=1)

        assert result is True
        mock_product_repo.delete.assert_called_once_with(sample_product)
        mock_product_repo.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_product_not_found(self, service, mock_product_repo):
        """Test delete returns False when product not found."""
        mock_product_repo.get_by_id.return_value = None

        result = await service.delete(product_id=999, user_id=1)

        assert result is False
        mock_product_repo.delete.assert_not_called()
        mock_product_repo.commit.assert_not_called()
