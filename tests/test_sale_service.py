import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date

from sales.service import SaleService
from sales.models import Sale, SaleItem
from sales.schemas import SaleCreate, SaleUpdate, CustomerSaleCreate, SaleItemCreate


class TestSaleService:
    """Unit tests for SaleService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock AsyncSession."""
        return AsyncMock()

    @pytest.fixture
    def mock_sale_repo(self):
        """Create a mock SaleRepository."""
        repo = AsyncMock()
        repo.get_by_id = AsyncMock()
        repo.get_all = AsyncMock()
        repo.add = AsyncMock()
        repo.update = AsyncMock()
        repo.delete = AsyncMock()
        repo.commit = AsyncMock()
        repo.flush = AsyncMock()
        repo.refresh = AsyncMock()
        repo.refetch_with_relations = AsyncMock()
        return repo

    @pytest.fixture
    def mock_sale_item_repo(self):
        """Create a mock SaleItemRepository."""
        repo = AsyncMock()
        repo.add = AsyncMock()
        repo.delete = AsyncMock()
        return repo

    @pytest.fixture
    def mock_product_service(self):
        """Create a mock ProductService."""
        service = AsyncMock()
        service.get_by_id = AsyncMock()
        return service

    @pytest.fixture
    def mock_customer_service(self):
        """Create a mock CustomerService."""
        service = AsyncMock()
        service.get_by_id = AsyncMock()
        return service

    @pytest.fixture
    def service(self, mock_db, mock_sale_repo, mock_sale_item_repo, mock_product_service, mock_customer_service):
        """Create a SaleService with mocked dependencies."""
        service = SaleService(mock_db)
        service.sale_repo = mock_sale_repo
        service.sale_item_repo = mock_sale_item_repo
        service.product_service = mock_product_service
        service.customer_service = mock_customer_service
        return service

    @pytest.fixture
    def sample_sale(self):
        """Create a sample sale for testing."""
        sale = MagicMock(spec=Sale)
        sale.id = 1
        sale.user_id = 1
        sale.date = date(2024, 1, 15)
        sale.status = "draft"
        sale.items = []
        return sale

    @pytest.fixture
    def sample_product(self):
        """Create a sample product for testing."""
        product = MagicMock()
        product.id = 1
        product.name = "Test Product"
        product.buy_price = 10.0
        product.sell_price = 15.0
        return product

    @pytest.fixture
    def sample_customer(self):
        """Create a sample customer for testing."""
        customer = MagicMock()
        customer.id = 1
        customer.name = "Test Customer"
        return customer

    @pytest.fixture
    def sale_create_data(self):
        """Create sample SaleCreate data."""
        return SaleCreate(
            date=date(2024, 1, 15),
            customer_sales=[
                CustomerSaleCreate(
                    customer_id=1,
                    products=[
                        SaleItemCreate(product_id=1, quantity=5)
                    ]
                )
            ]
        )

    # =========================================================================
    # get_all tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_all_returns_sales(self, service, mock_sale_repo, sample_sale):
        """Test get_all returns list of sales from repository."""
        mock_sale_repo.get_all.return_value = [sample_sale]

        result = await service.get_all(user_id=1)

        assert len(result) == 1
        assert result[0] == sample_sale
        mock_sale_repo.get_all.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_all_empty(self, service, mock_sale_repo):
        """Test get_all returns empty list when no sales."""
        mock_sale_repo.get_all.return_value = []

        result = await service.get_all(user_id=1)

        assert result == []

    # =========================================================================
    # get_by_id tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, service, mock_sale_repo, sample_sale):
        """Test get_by_id returns sale when found."""
        mock_sale_repo.get_by_id.return_value = sample_sale

        result = await service.get_by_id(sale_id=1, user_id=1)

        assert result == sample_sale
        mock_sale_repo.get_by_id.assert_called_once_with(1, 1)

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service, mock_sale_repo):
        """Test get_by_id returns None when sale not found."""
        mock_sale_repo.get_by_id.return_value = None

        result = await service.get_by_id(sale_id=999, user_id=1)

        assert result is None

    # =========================================================================
    # create tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_create_sale_success(
        self, service, mock_sale_repo, mock_sale_item_repo,
        mock_product_service, mock_customer_service,
        sale_create_data, sample_sale, sample_product, sample_customer
    ):
        """Test create successfully creates sale with items."""
        mock_customer_service.get_by_id.return_value = sample_customer
        mock_product_service.get_by_id.return_value = sample_product

        async def capture_add(sale):
            sale.id = 1
            return sale

        mock_sale_repo.add.side_effect = capture_add
        mock_sale_repo.refetch_with_relations.return_value = sample_sale

        result = await service.create(sale_create_data, user_id=1)

        assert result == sample_sale
        mock_sale_repo.add.assert_called_once()
        mock_sale_repo.flush.assert_called_once()
        mock_sale_item_repo.add.assert_called_once()
        mock_sale_repo.commit.assert_called_once()
        mock_sale_repo.refetch_with_relations.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_sale_customer_not_found(
        self, service, mock_customer_service, sale_create_data
    ):
        """Test create raises ValueError when customer not found."""
        mock_customer_service.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Customer 1 not found"):
            await service.create(sale_create_data, user_id=1)

    @pytest.mark.asyncio
    async def test_create_sale_product_not_found(
        self, service, mock_customer_service, mock_product_service,
        sale_create_data, sample_customer
    ):
        """Test create raises ValueError when product not found."""
        mock_customer_service.get_by_id.return_value = sample_customer
        mock_product_service.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Product 1 not found"):
            await service.create(sale_create_data, user_id=1)

    # =========================================================================
    # update tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_update_sale_success(
        self, service, mock_sale_repo, mock_sale_item_repo,
        mock_product_service, mock_customer_service,
        sample_sale, sample_product, sample_customer
    ):
        """Test update successfully updates sale."""
        update_data = SaleUpdate(
            date=date(2024, 2, 20),
            customer_sales=[
                CustomerSaleCreate(
                    customer_id=1,
                    products=[SaleItemCreate(product_id=1, quantity=10)]
                )
            ]
        )

        mock_sale_repo.get_by_id.return_value = sample_sale
        mock_customer_service.get_by_id.return_value = sample_customer
        mock_product_service.get_by_id.return_value = sample_product
        mock_sale_repo.refetch_with_relations.return_value = sample_sale

        result = await service.update(sale_id=1, sale_in=update_data, user_id=1)

        assert result == sample_sale
        assert sample_sale.date == date(2024, 2, 20)
        mock_sale_repo.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_sale_not_found(self, service, mock_sale_repo):
        """Test update returns None when sale not found."""
        update_data = SaleUpdate(
            date=date(2024, 2, 20),
            customer_sales=[]
        )
        mock_sale_repo.get_by_id.return_value = None

        result = await service.update(sale_id=999, sale_in=update_data, user_id=1)

        assert result is None
        mock_sale_repo.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_sale_customer_not_found(
        self, service, mock_sale_repo, mock_customer_service, sample_sale
    ):
        """Test update raises ValueError when customer not found."""
        update_data = SaleUpdate(
            date=date(2024, 2, 20),
            customer_sales=[
                CustomerSaleCreate(
                    customer_id=999,
                    products=[SaleItemCreate(product_id=1, quantity=10)]
                )
            ]
        )

        mock_sale_repo.get_by_id.return_value = sample_sale
        mock_customer_service.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Customer 999 not found"):
            await service.update(sale_id=1, sale_in=update_data, user_id=1)

    # =========================================================================
    # delete tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_delete_sale_success(self, service, mock_sale_repo, sample_sale):
        """Test delete successfully removes sale."""
        mock_sale_repo.get_by_id.return_value = sample_sale
        mock_sale_repo.delete.return_value = True

        result = await service.delete(sale_id=1, user_id=1)

        assert result is True
        mock_sale_repo.delete.assert_called_once_with(sample_sale)
        mock_sale_repo.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_sale_not_found(self, service, mock_sale_repo):
        """Test delete returns False when sale not found."""
        mock_sale_repo.get_by_id.return_value = None

        result = await service.delete(sale_id=999, user_id=1)

        assert result is False
        mock_sale_repo.delete.assert_not_called()
        mock_sale_repo.commit.assert_not_called()

    # =========================================================================
    # _validate_sale_data tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_validate_sale_data_success(
        self, service, mock_customer_service, mock_product_service,
        sale_create_data, sample_customer, sample_product
    ):
        """Test validation passes when all customers and products exist."""
        mock_customer_service.get_by_id.return_value = sample_customer
        mock_product_service.get_by_id.return_value = sample_product

        # Should not raise
        await service._validate_sale_data(sale_create_data, user_id=1)

        mock_customer_service.get_by_id.assert_called()
        mock_product_service.get_by_id.assert_called()

    @pytest.mark.asyncio
    async def test_validate_sale_data_missing_customer(
        self, service, mock_customer_service, sale_create_data
    ):
        """Test validation raises error when customer missing."""
        mock_customer_service.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Customer 1 not found"):
            await service._validate_sale_data(sale_create_data, user_id=1)

    @pytest.mark.asyncio
    async def test_validate_sale_data_missing_product(
        self, service, mock_customer_service, mock_product_service,
        sale_create_data, sample_customer
    ):
        """Test validation raises error when product missing."""
        mock_customer_service.get_by_id.return_value = sample_customer
        mock_product_service.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Product 1 not found"):
            await service._validate_sale_data(sale_create_data, user_id=1)
