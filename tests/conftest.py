import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from main import app
from core.database import get_db
from auth.dependencies import get_current_user


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_current_user():
    return "test_user"


@pytest.fixture
def client(mock_db, mock_current_user):
    async def override_get_db():
        yield mock_db
    
    def override_get_current_user():
        return mock_current_user
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def mock_product():
    return {"id": 1, "name": "Test Product", "description": "Test", "buy_price": 10.0, "sell_price": 15.0}


@pytest.fixture
def mock_provider():
    return {"id": 1, "name": "Test Provider", "email": "test@provider.com", "phone": "123-456-7890", "address": "123 Test St"}
