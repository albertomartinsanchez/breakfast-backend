import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from customers.repository import CustomerRepository, CustomerAccessTokenRepository
from customers.models import Customer
from customers.models_access_token import CustomerAccessToken


class TestCustomerRepository:
    """Unit tests for CustomerRepository."""

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
        """Create a CustomerRepository with mocked db."""
        return CustomerRepository(mock_db)

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

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repository, mock_db, sample_customer):
        """Test get_by_id returns customer when found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_customer
        mock_db.execute.return_value = mock_result

        result = await repository.get_by_id(1, user_id=1)

        assert result == sample_customer
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, mock_db):
        """Test get_by_id returns None when customer not found."""
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
    async def test_get_all_returns_customers(self, repository, mock_db, sample_customer):
        """Test get_all returns list of customers."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_customer]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await repository.get_all(user_id=1)

        assert len(result) == 1
        assert result[0] == sample_customer

    @pytest.mark.asyncio
    async def test_get_all_empty(self, repository, mock_db):
        """Test get_all returns empty list when no customers."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await repository.get_all(user_id=1)

        assert result == []

    @pytest.mark.asyncio
    async def test_add_customer(self, repository, mock_db, sample_customer):
        """Test add adds customer to session."""
        result = await repository.add(sample_customer)

        assert result == sample_customer
        mock_db.add.assert_called_once_with(sample_customer)

    @pytest.mark.asyncio
    async def test_update_customer(self, repository, sample_customer):
        """Test update returns the entity (SQLAlchemy tracks changes)."""
        result = await repository.update(sample_customer)

        assert result == sample_customer

    @pytest.mark.asyncio
    async def test_delete_customer(self, repository, mock_db, sample_customer):
        """Test delete removes customer from session."""
        result = await repository.delete(sample_customer)

        assert result is True
        mock_db.delete.assert_called_once_with(sample_customer)

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
    async def test_refresh(self, repository, mock_db, sample_customer):
        """Test refresh calls db.refresh."""
        await repository.refresh(sample_customer)

        mock_db.refresh.assert_called_once_with(sample_customer)

    @pytest.mark.asyncio
    async def test_refresh_with_attributes(self, repository, mock_db, sample_customer):
        """Test refresh with specific attributes."""
        await repository.refresh(sample_customer, ["access_token"])

        mock_db.refresh.assert_called_once_with(sample_customer, ["access_token"])


class TestCustomerAccessTokenRepository:
    """Unit tests for CustomerAccessTokenRepository."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock AsyncSession."""
        db = AsyncMock()
        db.add = MagicMock()
        db.delete = AsyncMock()
        return db

    @pytest.fixture
    def repository(self, mock_db):
        """Create a CustomerAccessTokenRepository with mocked db."""
        return CustomerAccessTokenRepository(mock_db)

    @pytest.fixture
    def sample_token(self):
        """Create a sample access token for testing."""
        token = MagicMock(spec=CustomerAccessToken)
        token.id = 1
        token.customer_id = 1
        token.access_token = "test-uuid-token"
        return token

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repository, mock_db, sample_token):
        """Test get_by_id returns token when found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_token
        mock_db.execute.return_value = mock_result

        result = await repository.get_by_id(1, user_id=1)

        assert result == sample_token

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, mock_db):
        """Test get_by_id returns None when token not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repository.get_by_id(999, user_id=1)

        assert result is None

    @pytest.mark.asyncio
    async def test_add_token(self, repository, mock_db, sample_token):
        """Test add adds token to session."""
        result = await repository.add(sample_token)

        assert result == sample_token
        mock_db.add.assert_called_once_with(sample_token)

    @pytest.mark.asyncio
    async def test_delete_token(self, repository, mock_db, sample_token):
        """Test delete removes token from session."""
        result = await repository.delete(sample_token)

        assert result is True
        mock_db.delete.assert_called_once_with(sample_token)

    @pytest.mark.asyncio
    async def test_get_all_returns_empty(self, repository, mock_db):
        """Test get_all returns empty list (not typically used for tokens)."""
        result = await repository.get_all(user_id=1)

        assert result == []
