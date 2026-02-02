import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from customers.models import Customer


class TestCustomers:
    @pytest.mark.asyncio
    async def test_get_customers(self, client):
        """Test GET /customers/ returns empty list."""
        with patch('customers.service.CustomerService.get_all', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []
            response = await client.get("/customers/")
            assert response.status_code == 200
            assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_customers_with_data(self, client):
        """Test GET /customers/ returns customer list."""
        mock_customer = MagicMock(spec=Customer)
        mock_customer.id = 1
        mock_customer.user_id = 1
        mock_customer.name = "John Doe"
        mock_customer.address = "123 Main St"
        mock_customer.phone = "555-1234"
        mock_customer.credit = 100.0
        mock_customer.access_token = None

        with patch('customers.service.CustomerService.get_all', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [mock_customer]
            response = await client.get("/customers/")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == "John Doe"

    @pytest.mark.asyncio
    async def test_get_customer_by_id(self, client):
        """Test GET /customers/{id} returns customer."""
        mock_customer = MagicMock(spec=Customer)
        mock_customer.id = 1
        mock_customer.user_id = 1
        mock_customer.name = "John Doe"
        mock_customer.address = "123 Main St"
        mock_customer.phone = "555-1234"
        mock_customer.credit = 100.0
        mock_customer.access_token = None

        with patch('customers.service.CustomerService.get_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_customer
            response = await client.get("/customers/1")
            assert response.status_code == 200
            assert response.json()["name"] == "John Doe"

    @pytest.mark.asyncio
    async def test_get_customer_not_found(self, client):
        """Test GET /customers/{id} returns 404 when not found."""
        with patch('customers.service.CustomerService.get_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            response = await client.get("/customers/999")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_customer(self, client):
        """Test POST /customers/ creates customer."""
        mock_customer = MagicMock(spec=Customer)
        mock_customer.id = 1
        mock_customer.user_id = 1
        mock_customer.name = "New Customer"
        mock_customer.address = "456 Oak Ave"
        mock_customer.phone = "555-9999"
        mock_customer.credit = 0.0
        mock_customer.access_token = None

        with patch('customers.service.CustomerService.create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_customer
            response = await client.post("/customers/", json={
                "name": "New Customer",
                "address": "456 Oak Ave",
                "phone": "555-9999"
            })
            assert response.status_code == 201
            assert response.json()["name"] == "New Customer"

    @pytest.mark.asyncio
    async def test_update_customer(self, client):
        """Test PUT /customers/{id} updates customer."""
        mock_customer = MagicMock(spec=Customer)
        mock_customer.id = 1
        mock_customer.user_id = 1
        mock_customer.name = "Updated Name"
        mock_customer.address = "New Address"
        mock_customer.phone = "555-0000"
        mock_customer.credit = 50.0
        mock_customer.access_token = None

        with patch('customers.service.CustomerService.update', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = mock_customer
            response = await client.put("/customers/1", json={
                "name": "Updated Name",
                "address": "New Address",
                "phone": "555-0000",
                "credit": 50.0
            })
            assert response.status_code == 200
            assert response.json()["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_customer_not_found(self, client):
        """Test PUT /customers/{id} returns 404 when not found."""
        with patch('customers.service.CustomerService.update', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = None
            response = await client.put("/customers/999", json={
                "name": "Updated Name"
            })
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_customer(self, client):
        """Test DELETE /customers/{id} deletes customer."""
        with patch('customers.service.CustomerService.delete', new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = True
            response = await client.delete("/customers/1")
            assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_customer_not_found(self, client):
        """Test DELETE /customers/{id} returns 404 when not found."""
        with patch('customers.service.CustomerService.delete', new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = False
            response = await client.delete("/customers/999")
            assert response.status_code == 404
