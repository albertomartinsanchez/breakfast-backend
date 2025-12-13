import pytest
from unittest.mock import AsyncMock, MagicMock, patch

class TestCustomers:
    @pytest.mark.asyncio
    async def test_get_customers(self, client):
        with patch('customers.crud.get_customers', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []
            response = client.get("/customers/")
            assert response.status_code == 200
