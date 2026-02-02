import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from customers.service import CustomerService
from customers.models import Customer
from customers.models_access_token import CustomerAccessToken
from customers.schemas import CustomerCreate, CustomerUpdate


class TestCustomerService:
    """Unit tests for CustomerService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock AsyncSession."""
        return AsyncMock()

    @pytest.fixture
    def mock_customer_repo(self):
        """Create a mock CustomerRepository."""
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
    def mock_token_repo(self):
        """Create a mock CustomerAccessTokenRepository."""
        repo = AsyncMock()
        repo.add = AsyncMock()
        return repo

    @pytest.fixture
    def service(self, mock_db, mock_customer_repo, mock_token_repo):
        """Create a CustomerService with mocked repositories."""
        service = CustomerService(mock_db)
        service.customer_repo = mock_customer_repo
        service.token_repo = mock_token_repo
        return service

    @pytest.fixture
    def sample_customer(self):
        """Create a sample customer for testing."""
        customer = MagicMock(spec=Customer)
        customer.id = 1
        customer.user_id = 1
        customer.name = "John Doe"
        customer.address = "123 Main St"
        customer.phone = "555-1234"
        customer.name_index = "hashed_name"
        customer.credit = 100.0
        customer.access_token = None
        return customer

    @pytest.fixture
    def customer_create_data(self):
        """Create sample CustomerCreate data."""
        return CustomerCreate(
            name="John Doe",
            address="123 Main St",
            phone="555-1234",
            credit=100.0
        )

    @pytest.fixture
    def customer_update_data(self):
        """Create sample CustomerUpdate data."""
        return CustomerUpdate(
            name="Jane Doe",
            address="456 Oak Ave",
            phone="555-5678",
            credit=200.0
        )

    # =========================================================================
    # get_all tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_all_returns_customers(self, service, mock_customer_repo, sample_customer):
        """Test get_all returns list of customers from repository."""
        mock_customer_repo.get_all.return_value = [sample_customer]

        result = await service.get_all(user_id=1)

        assert len(result) == 1
        assert result[0] == sample_customer
        mock_customer_repo.get_all.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_all_empty(self, service, mock_customer_repo):
        """Test get_all returns empty list when no customers."""
        mock_customer_repo.get_all.return_value = []

        result = await service.get_all(user_id=1)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_all_multiple_customers(self, service, mock_customer_repo):
        """Test get_all returns multiple customers."""
        customers = [MagicMock(spec=Customer) for _ in range(3)]
        mock_customer_repo.get_all.return_value = customers

        result = await service.get_all(user_id=1)

        assert len(result) == 3

    # =========================================================================
    # get_by_id tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, service, mock_customer_repo, sample_customer):
        """Test get_by_id returns customer when found."""
        mock_customer_repo.get_by_id.return_value = sample_customer

        result = await service.get_by_id(customer_id=1, user_id=1)

        assert result == sample_customer
        mock_customer_repo.get_by_id.assert_called_once_with(1, 1)

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service, mock_customer_repo):
        """Test get_by_id returns None when customer not found."""
        mock_customer_repo.get_by_id.return_value = None

        result = await service.get_by_id(customer_id=999, user_id=1)

        assert result is None

    # =========================================================================
    # create tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_create_customer_success(
        self, service, mock_customer_repo, mock_token_repo, customer_create_data
    ):
        """Test create successfully creates customer with access token."""
        # Capture the customer object when add is called
        captured_customer = None
        async def capture_add(customer):
            nonlocal captured_customer
            captured_customer = customer
            customer.id = 1  # Simulate DB assigning ID after flush
            return customer

        mock_customer_repo.add.side_effect = capture_add

        with patch('customers.service.blind_index', return_value='hashed_index'):
            result = await service.create(customer_create_data, user_id=1)

        # Verify customer was added with correct attributes
        mock_customer_repo.add.assert_called_once()
        assert captured_customer is not None
        assert captured_customer.name == "John Doe"
        assert captured_customer.address == "123 Main St"
        assert captured_customer.phone == "555-1234"
        assert captured_customer.credit == 100.0
        assert captured_customer.user_id == 1
        assert captured_customer.name_index == 'hashed_index'

        # Verify flush was called after adding customer
        mock_customer_repo.flush.assert_called_once()

        # Verify access token was created
        mock_token_repo.add.assert_called_once()
        added_token = mock_token_repo.add.call_args[0][0]
        assert added_token.customer_id == 1

        # Verify commit and refresh
        mock_customer_repo.commit.assert_called_once()
        mock_customer_repo.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_customer_with_zero_credit(self, service, mock_customer_repo, mock_token_repo):
        """Test create with zero credit defaults correctly."""
        customer_data = CustomerCreate(name="Test User")
        created_customer = MagicMock(spec=Customer)
        created_customer.id = 1
        mock_customer_repo.add.return_value = created_customer

        with patch('customers.service.blind_index', return_value='hashed'):
            await service.create(customer_data, user_id=1)

        added_customer = mock_customer_repo.add.call_args[0][0]
        assert added_customer.credit == 0.0

    @pytest.mark.asyncio
    async def test_create_customer_generates_blind_index(
        self, service, mock_customer_repo, mock_token_repo, customer_create_data
    ):
        """Test create generates blind index for name."""
        created_customer = MagicMock(spec=Customer)
        created_customer.id = 1
        mock_customer_repo.add.return_value = created_customer

        with patch('customers.service.blind_index', return_value='test_blind_index') as mock_blind:
            await service.create(customer_create_data, user_id=1)

        mock_blind.assert_called_once_with("John Doe")
        added_customer = mock_customer_repo.add.call_args[0][0]
        assert added_customer.name_index == 'test_blind_index'

    @pytest.mark.asyncio
    async def test_create_customer_generates_unique_token(
        self, service, mock_customer_repo, mock_token_repo, customer_create_data
    ):
        """Test create generates unique access token."""
        created_customer = MagicMock(spec=Customer)
        created_customer.id = 1
        mock_customer_repo.add.return_value = created_customer

        with patch('customers.service.blind_index', return_value='hashed'):
            await service.create(customer_create_data, user_id=1)

        added_token = mock_token_repo.add.call_args[0][0]
        assert added_token.access_token is not None
        assert len(added_token.access_token) > 0

    # =========================================================================
    # update tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_update_customer_success(
        self, service, mock_customer_repo, sample_customer, customer_update_data
    ):
        """Test update successfully updates customer."""
        mock_customer_repo.get_by_id.return_value = sample_customer

        with patch('customers.service.blind_index', return_value='new_hashed_index'):
            result = await service.update(customer_id=1, customer_in=customer_update_data, user_id=1)

        assert result == sample_customer
        assert sample_customer.name == "Jane Doe"
        assert sample_customer.address == "456 Oak Ave"
        assert sample_customer.phone == "555-5678"
        assert sample_customer.credit == 200.0
        mock_customer_repo.commit.assert_called_once()
        mock_customer_repo.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_customer_not_found(self, service, mock_customer_repo, customer_update_data):
        """Test update returns None when customer not found."""
        mock_customer_repo.get_by_id.return_value = None

        result = await service.update(customer_id=999, customer_in=customer_update_data, user_id=1)

        assert result is None
        mock_customer_repo.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_customer_regenerates_blind_index(
        self, service, mock_customer_repo, sample_customer, customer_update_data
    ):
        """Test update regenerates blind index when name changes."""
        mock_customer_repo.get_by_id.return_value = sample_customer

        with patch('customers.service.blind_index', return_value='updated_blind_index') as mock_blind:
            await service.update(customer_id=1, customer_in=customer_update_data, user_id=1)

        mock_blind.assert_called_once_with("Jane Doe")
        assert sample_customer.name_index == 'updated_blind_index'

    @pytest.mark.asyncio
    async def test_update_customer_without_credit(self, service, mock_customer_repo, sample_customer):
        """Test update preserves credit when not provided."""
        original_credit = sample_customer.credit
        update_data = CustomerUpdate(name="New Name", address=None, phone=None, credit=None)
        mock_customer_repo.get_by_id.return_value = sample_customer

        with patch('customers.service.blind_index', return_value='hashed'):
            await service.update(customer_id=1, customer_in=update_data, user_id=1)

        assert sample_customer.credit == original_credit

    @pytest.mark.asyncio
    async def test_update_customer_with_zero_credit(self, service, mock_customer_repo, sample_customer):
        """Test update can set credit to zero."""
        update_data = CustomerUpdate(name="Name", credit=0.0)
        mock_customer_repo.get_by_id.return_value = sample_customer

        with patch('customers.service.blind_index', return_value='hashed'):
            await service.update(customer_id=1, customer_in=update_data, user_id=1)

        assert sample_customer.credit == 0.0

    # =========================================================================
    # delete tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_delete_customer_success(self, service, mock_customer_repo, sample_customer):
        """Test delete successfully removes customer."""
        mock_customer_repo.get_by_id.return_value = sample_customer
        mock_customer_repo.delete.return_value = True

        result = await service.delete(customer_id=1, user_id=1)

        assert result is True
        mock_customer_repo.delete.assert_called_once_with(sample_customer)
        mock_customer_repo.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_customer_not_found(self, service, mock_customer_repo):
        """Test delete returns False when customer not found."""
        mock_customer_repo.get_by_id.return_value = None

        result = await service.delete(customer_id=999, user_id=1)

        assert result is False
        mock_customer_repo.delete.assert_not_called()
        mock_customer_repo.commit.assert_not_called()

    # =========================================================================
    # _generate_access_token tests
    # =========================================================================

    def test_generate_access_token_returns_string(self, service):
        """Test _generate_access_token returns a string."""
        token = service._generate_access_token()

        assert isinstance(token, str)
        assert len(token) > 0

    def test_generate_access_token_unique(self, service):
        """Test _generate_access_token generates unique tokens."""
        tokens = [service._generate_access_token() for _ in range(100)]

        assert len(set(tokens)) == 100  # All tokens should be unique

    def test_generate_access_token_uuid_format(self, service):
        """Test _generate_access_token returns UUID format."""
        token = service._generate_access_token()

        # UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        parts = token.split('-')
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12
