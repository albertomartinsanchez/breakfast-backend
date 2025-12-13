import pytest
from unittest.mock import AsyncMock, MagicMock, patch

class TestProducts:
    @pytest.mark.asyncio
    async def test_get_products(self, client):
        with patch('products.crud.get_products', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []
            response = client.get("/products/")
            assert response.status_code == 200
