import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
from main import app
from core.database import get_db
from auth.dependencies import get_current_user
from auth.models import User

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = 1
    user.email = "test@example.com"
    return user

@pytest.fixture
def client(mock_db, mock_user):
    async def override_get_db():
        yield mock_db
    async def override_get_current_user():
        return mock_user
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def public_client():
    with TestClient(app) as test_client:
        yield test_client
