import pytest
from unittest.mock import AsyncMock, patch

class TestSignup:
    @pytest.mark.asyncio
    async def test_signup_success(self, public_client):
        # Patch where functions are USED (in router), not where they're DEFINED (in crud)
        with patch('auth.router.get_user_by_email', new_callable=AsyncMock) as mock_get, \
             patch('auth.router.create_user', new_callable=AsyncMock) as mock_create:
            
            # Mock: No existing user
            mock_get.return_value = None
            
            # Mock: Created user
            class MockUser:
                id = 1
                email = "new@example.com"
            
            mock_create.return_value = MockUser()
            
            # Make async request
            response = await public_client.post(
                "/auth/signup",
                json={"email": "new@example.com", "password": "password123"}
            )
            
            # Assertions
            assert response.status_code == 201
            data = response.json()
            assert data["email"] == "new@example.com"
            assert data["id"] == 1
            
            # Verify mocks were called correctly
            mock_get.assert_called_once()
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_signup_duplicate_email(self, public_client):
        with patch('auth.router.get_user_by_email', new_callable=AsyncMock) as mock_get:
            # Mock: User already exists
            class ExistingUser:
                id = 1
                email = "existing@example.com"
            
            mock_get.return_value = ExistingUser()
            
            response = await public_client.post(
                "/auth/signup",
                json={"email": "existing@example.com", "password": "password123"}
            )
            
            # Should return 400 Bad Request
            assert response.status_code == 400
            assert "already registered" in response.json()["detail"].lower()
            
            # Verify get was called, but create was NOT called
            mock_get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_signup_invalid_email(self, public_client):
        # No mocking needed - tests validation logic
        response = await public_client.post(
            "/auth/signup",
            json={"email": "not-an-email", "password": "password123"}
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_signup_short_password(self, public_client):
        # No mocking needed - tests validation logic
        response = await public_client.post(
            "/auth/signup",
            json={"email": "test@example.com", "password": "short"}
        )
        
        assert response.status_code == 422  # Validation error