import pytest
from httpx import AsyncClient
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
async def client(mock_db, mock_user):
    async def override_get_db():
        yield mock_db
    async def override_get_current_user():
        return mock_user
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    async with AsyncClient(app=app, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
async def public_client():
    async with AsyncClient(app=app, base_url="http://test") as test_client:
        yield test_client
