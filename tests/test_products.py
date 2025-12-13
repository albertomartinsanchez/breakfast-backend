import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestGetProducts:
    @pytest.mark.asyncio
    async def test_get_products_success(self, client, mock_db):
        with patch('products.crud.get_products', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []
            response = client.get("/products/")
            assert response.status_code == 200


class TestCreateProduct:
    @pytest.mark.asyncio
    async def test_create_product_success(self, client, mock_db):
        product_data = {"name": "New", "buy_price": 10.0, "sell_price": 15.0}
        with patch('products.crud.create_product', new_callable=AsyncMock) as mock_create:
            mock_obj = MagicMock(**{**product_data, "id": 1})
            mock_create.return_value = mock_obj
            response = client.post("/products/", json=product_data)
            assert response.status_code == 201
