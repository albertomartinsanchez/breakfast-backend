import pytest
from unittest.mock import AsyncMock, MagicMock, patch

class TestSales:
    @pytest.mark.asyncio
    async def test_get_sales(self, client):
        with patch('sales.crud.get_sales', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []
            response = client.get("/sales/")
            assert response.status_code == 200
