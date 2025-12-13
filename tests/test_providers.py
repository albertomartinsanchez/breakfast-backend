import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestGetProviders:
    @pytest.mark.asyncio
    async def test_get_providers_success(self, client, mock_db):
        with patch('providers.crud.get_providers', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []
            response = client.get("/providers/")
            assert response.status_code == 200


class TestCreateProvider:
    @pytest.mark.asyncio
    async def test_create_provider_success(self, client, mock_db):
        provider_data = {"name": "New", "email": "new@test.com"}
        with patch('providers.crud.get_provider_by_email', new_callable=AsyncMock) as mock_check,              patch('providers.crud.create_provider', new_callable=AsyncMock) as mock_create:
            mock_check.return_value = None
            mock_obj = MagicMock(**{**provider_data, "id": 1})
            mock_create.return_value = mock_obj
            response = client.post("/providers/", json=provider_data)
            assert response.status_code == 201
    
    @pytest.mark.asyncio
    async def test_create_provider_duplicate_email(self, client, mock_db):
        provider_data = {"name": "New", "email": "existing@test.com"}
        with patch('providers.crud.get_provider_by_email', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = MagicMock(id=1)
            response = client.post("/providers/", json=provider_data)
            assert response.status_code == 400
