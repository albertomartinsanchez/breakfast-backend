import pytest
from unittest.mock import AsyncMock, MagicMock, patch

class TestSignup:
    @pytest.mark.asyncio
    async def test_signup_success(self, public_client):
        with patch('auth.crud.get_user_by_email', new_callable=AsyncMock) as mock_get,              patch('auth.crud.create_user', new_callable=AsyncMock) as mock_create:
            mock_get.return_value = None
            mock_user = MagicMock(id=1, email="new@example.com")
            mock_create.return_value = mock_user
            response = public_client.post("/auth/signup", json={"email": "new@example.com", "password": "password123"})
            assert response.status_code == 201

class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, public_client):
        with patch('auth.crud.get_user_by_email', new_callable=AsyncMock) as mock_get,              patch('core.security.verify_password') as mock_verify:
            mock_user = MagicMock(id=1, email="test@example.com", hashed_password="hashed")
            mock_get.return_value = mock_user
            mock_verify.return_value = True
            response = public_client.post("/auth/login", json={"email": "test@example.com", "password": "password123"})
            assert response.status_code == 200
            assert "access_token" in response.json()
