"""
Pytest configuration and fixtures for testing
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock

from main import app
from database import get_db
from auth import get_current_user

# Mock database session
@pytest.fixture
def mock_db():
    return AsyncMock()

# Mock authenticated user
@pytest.fixture
def mock_current_user():
    return "test_user"

# Test client fixture
@pytest.fixture
async def client(mock_db, mock_current_user):
    # Override dependencies
    async def override_get_db():
        yield mock_db

    def override_get_current_user():
        return mock_current_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# Mock products for testing
@pytest.fixture
def mock_product():
    return {
        "id": 1,
        "name": "Test Product",
        "description": "Test Description",
        "buy_price": 10.0,
        "sell_price": 15.0
    }


@pytest.fixture
def mock_product_list(mock_product):
    return [
        mock_product,
        {
            "id": 2,
            "name": "Another Product",
            "description": "Another Description",
            "buy_price": 20.0,
            "sell_price": 30.0
        }
    ]
