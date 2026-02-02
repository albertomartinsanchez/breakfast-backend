import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date


class TestGetSales:
    @pytest.mark.asyncio
    async def test_get_sales_empty(self, client):
        """Test getting sales when none exist."""
        with patch('sales.service.SaleService.get_all', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []

            response = await client.get("/sales/")

            assert response.status_code == 200
            assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_sales_with_data(self, client):
        """Test getting sales with data."""
        with patch('sales.service.SaleService.get_all', new_callable=AsyncMock) as mock_get:
            # Create mock sale with items
            mock_item = MagicMock()
            mock_item.customer_id = 1
            mock_item.product_id = 1
            mock_item.quantity = 5
            mock_item.buy_price_at_sale = 10.0
            mock_item.sell_price_at_sale = 15.0
            mock_item.product = MagicMock(name="Product 1")
            mock_item.product.name = "Product 1"
            mock_item.customer = MagicMock(name="Customer 1")
            mock_item.customer.name = "Customer 1"

            mock_sale = MagicMock()
            mock_sale.id = 1
            mock_sale.user_id = 1
            mock_sale.date = date(2024, 1, 15)
            mock_sale.status = "draft"
            mock_sale.items = [mock_item]

            mock_get.return_value = [mock_sale]

            response = await client.get("/sales/")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == 1
            assert data[0]["status"] == "draft"

    @pytest.mark.asyncio
    async def test_get_sales_unauthorized(self, public_client):
        """Test getting sales without authentication."""
        response = await public_client.get("/sales/")
        assert response.status_code == 403


class TestGetSaleById:
    @pytest.mark.asyncio
    async def test_get_sale_by_id_success(self, client):
        """Test getting a specific sale by ID."""
        with patch('sales.service.SaleService.get_by_id', new_callable=AsyncMock) as mock_get:
            mock_item = MagicMock()
            mock_item.customer_id = 1
            mock_item.product_id = 1
            mock_item.quantity = 5
            mock_item.buy_price_at_sale = 10.0
            mock_item.sell_price_at_sale = 15.0
            mock_item.product = MagicMock()
            mock_item.product.name = "Product 1"
            mock_item.customer = MagicMock()
            mock_item.customer.name = "Customer 1"

            mock_sale = MagicMock()
            mock_sale.id = 1
            mock_sale.user_id = 1
            mock_sale.date = date(2024, 1, 15)
            mock_sale.status = "draft"
            mock_sale.items = [mock_item]

            mock_get.return_value = mock_sale

            response = await client.get("/sales/1")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1

    @pytest.mark.asyncio
    async def test_get_sale_by_id_not_found(self, client):
        """Test getting non-existent sale."""
        with patch('sales.service.SaleService.get_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            response = await client.get("/sales/999")

            assert response.status_code == 404
            assert "999" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_sale_unauthorized(self, public_client):
        """Test getting sale without authentication."""
        response = await public_client.get("/sales/1")
        assert response.status_code == 403


class TestCreateSale:
    @pytest.mark.asyncio
    async def test_create_sale_success(self, client):
        """Test creating a sale successfully."""
        sale_data = {
            "date": "2024-01-15",
            "customer_sales": [
                {
                    "customer_id": 1,
                    "products": [
                        {"product_id": 1, "quantity": 5}
                    ]
                }
            ]
        }

        with patch('sales.service.SaleService.create', new_callable=AsyncMock) as mock_create, \
             patch('customers.service.CustomerService.get_all', new_callable=AsyncMock) as mock_customers, \
             patch('notifications.events.notify_sale_open', new_callable=AsyncMock):

            mock_item = MagicMock()
            mock_item.customer_id = 1
            mock_item.product_id = 1
            mock_item.quantity = 5
            mock_item.buy_price_at_sale = 10.0
            mock_item.sell_price_at_sale = 15.0
            mock_item.product = MagicMock()
            mock_item.product.name = "Product 1"
            mock_item.customer = MagicMock()
            mock_item.customer.name = "Customer 1"

            mock_sale = MagicMock()
            mock_sale.id = 1
            mock_sale.user_id = 1
            mock_sale.date = date(2024, 1, 15)
            mock_sale.status = "draft"
            mock_sale.items = [mock_item]

            mock_create.return_value = mock_sale
            mock_customers.return_value = []

            response = await client.post("/sales/", json=sale_data)

            assert response.status_code == 201
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_sale_customer_not_found(self, client):
        """Test creating sale with non-existent customer."""
        sale_data = {
            "date": "2024-01-15",
            "customer_sales": [
                {
                    "customer_id": 999,
                    "products": [
                        {"product_id": 1, "quantity": 5}
                    ]
                }
            ]
        }

        with patch('sales.service.SaleService.create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = ValueError("Customer 999 not found")

            response = await client.post("/sales/", json=sale_data)

            assert response.status_code == 404
            assert "Customer 999 not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_sale_product_not_found(self, client):
        """Test creating sale with non-existent product."""
        sale_data = {
            "date": "2024-01-15",
            "customer_sales": [
                {
                    "customer_id": 1,
                    "products": [
                        {"product_id": 999, "quantity": 5}
                    ]
                }
            ]
        }

        with patch('sales.service.SaleService.create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = ValueError("Product 999 not found")

            response = await client.post("/sales/", json=sale_data)

            assert response.status_code == 404
            assert "Product 999 not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_sale_unauthorized(self, public_client):
        """Test creating sale without authentication."""
        sale_data = {
            "date": "2024-01-15",
            "customer_sales": []
        }

        response = await public_client.post("/sales/", json=sale_data)
        assert response.status_code == 403


class TestUpdateSale:
    @pytest.mark.asyncio
    async def test_update_sale_success(self, client):
        """Test updating a sale successfully."""
        update_data = {
            "date": "2024-02-20",
            "customer_sales": [
                {
                    "customer_id": 1,
                    "products": [
                        {"product_id": 1, "quantity": 10}
                    ]
                }
            ]
        }

        with patch('sales.service.SaleService.update', new_callable=AsyncMock) as mock_update:
            mock_item = MagicMock()
            mock_item.customer_id = 1
            mock_item.product_id = 1
            mock_item.quantity = 10
            mock_item.buy_price_at_sale = 10.0
            mock_item.sell_price_at_sale = 15.0
            mock_item.product = MagicMock()
            mock_item.product.name = "Product 1"
            mock_item.customer = MagicMock()
            mock_item.customer.name = "Customer 1"

            mock_sale = MagicMock()
            mock_sale.id = 1
            mock_sale.user_id = 1
            mock_sale.date = date(2024, 2, 20)
            mock_sale.status = "draft"
            mock_sale.items = [mock_item]

            mock_update.return_value = mock_sale

            response = await client.put("/sales/1", json=update_data)

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_sale_not_found(self, client):
        """Test updating non-existent sale."""
        update_data = {
            "date": "2024-02-20",
            "customer_sales": []
        }

        with patch('sales.service.SaleService.update', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = None

            response = await client.put("/sales/999", json=update_data)

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_sale_unauthorized(self, public_client):
        """Test updating sale without authentication."""
        update_data = {
            "date": "2024-02-20",
            "customer_sales": []
        }

        response = await public_client.put("/sales/1", json=update_data)
        assert response.status_code == 403


class TestDeleteSale:
    @pytest.mark.asyncio
    async def test_delete_sale_success(self, client):
        """Test deleting a sale successfully."""
        with patch('sales.service.SaleService.get_by_id', new_callable=AsyncMock) as mock_get, \
             patch('sales.service.SaleService.delete', new_callable=AsyncMock) as mock_delete, \
             patch('notifications.events.notify_sale_deleted', new_callable=AsyncMock):

            mock_sale = MagicMock()
            mock_sale.id = 1
            mock_sale.date = date(2024, 1, 15)
            mock_sale.items = []

            mock_get.return_value = mock_sale
            mock_delete.return_value = True

            response = await client.delete("/sales/1")

            assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_sale_not_found(self, client):
        """Test deleting non-existent sale."""
        with patch('sales.service.SaleService.get_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            response = await client.delete("/sales/999")

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_sale_unauthorized(self, public_client):
        """Test deleting sale without authentication."""
        response = await public_client.delete("/sales/1")
        assert response.status_code == 403
