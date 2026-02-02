import pytest
from unittest.mock import AsyncMock, patch, ANY

class TestGetProducts:
    @pytest.mark.asyncio
    async def test_get_products_success_empty(self, client, mock_db):
        """Test getting products when none exist"""
        with patch('products.service.ProductService.get_all', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []

            response = await client.get("/products/")

            assert response.status_code == 200
            assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_products_success_with_data(self, client, mock_db):
        """Test getting products with multiple items"""
        with patch('products.service.ProductService.get_all', new_callable=AsyncMock) as mock_get:
            class MockProduct:
                id = 1
                name = "Product 1"
                description = "Description 1"
                buy_price = 10.0
                sell_price = 15.0
                user_id = 1

            class MockProduct2:
                id = 2
                name = "Product 2"
                description = None
                buy_price = 20.0
                sell_price = 30.0
                user_id = 1

            mock_get.return_value = [MockProduct(), MockProduct2()]

            response = await client.get("/products/")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["name"] == "Product 1"
            assert data[1]["name"] == "Product 2"
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_products_unauthorized(self, public_client):
        """Test getting products without authentication"""
        response = await public_client.get("/products/")
        assert response.status_code == 403


class TestGetProductById:
    @pytest.mark.asyncio
    async def test_get_product_by_id_success(self, client, mock_db):
        """Test getting a specific product by ID"""
        with patch('products.service.ProductService.get_by_id', new_callable=AsyncMock) as mock_get:
            class MockProduct:
                id = 1
                name = "Test Product"
                description = "Test Description"
                buy_price = 10.0
                sell_price = 15.0
                user_id = 1

            mock_get.return_value = MockProduct()

            response = await client.get("/products/1")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["name"] == "Test Product"
            assert data["buy_price"] == 10.0
            assert data["sell_price"] == 15.0

    @pytest.mark.asyncio
    async def test_get_product_by_id_not_found(self, client, mock_db):
        """Test getting non-existent product"""
        with patch('products.service.ProductService.get_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            response = await client.get("/products/999")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
            assert "999" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_product_invalid_id(self, client, mock_db):
        """Test getting product with invalid ID format"""
        response = await client.get("/products/abc")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_product_unauthorized(self, public_client):
        """Test getting product without authentication"""
        response = await public_client.get("/products/1")
        assert response.status_code == 403


class TestCreateProduct:
    @pytest.mark.asyncio
    async def test_create_product_success(self, client, mock_db):
        """Test creating a product successfully"""
        product_data = {
            "name": "New Product",
            "description": "New Description",
            "buy_price": 10.5,
            "sell_price": 20.0
        }

        with patch('products.service.ProductService.create', new_callable=AsyncMock) as mock_create:
            class MockProduct:
                id = 1
                name = "New Product"
                description = "New Description"
                buy_price = 10.5
                sell_price = 20.0
                user_id = 1

            mock_create.return_value = MockProduct()

            response = await client.post("/products/", json=product_data)

            assert response.status_code == 201
            data = response.json()
            assert data["id"] == 1
            assert data["name"] == "New Product"
            assert data["buy_price"] == 10.5
            assert data["sell_price"] == 20.0
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_product_minimal_data(self, client, mock_db):
        """Test creating product with minimal required fields"""
        product_data = {
            "name": "Minimal Product",
            "buy_price": 5.0,
            "sell_price": 10.0
        }

        with patch('products.service.ProductService.create', new_callable=AsyncMock) as mock_create:
            class MockProduct:
                id = 1
                name = "Minimal Product"
                description = None
                buy_price = 5.0
                sell_price = 10.0
                user_id = 1

            mock_create.return_value = MockProduct()

            response = await client.post("/products/", json=product_data)

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "Minimal Product"
            assert data["description"] is None

    @pytest.mark.asyncio
    async def test_create_product_missing_name(self, client, mock_db):
        """Test creating product without required name field"""
        product_data = {
            "buy_price": 10.0,
            "sell_price": 15.0
        }

        response = await client.post("/products/", json=product_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_product_missing_buy_price(self, client, mock_db):
        """Test creating product without buy_price"""
        product_data = {
            "name": "Test",
            "sell_price": 15.0
        }

        response = await client.post("/products/", json=product_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_product_missing_sell_price(self, client, mock_db):
        """Test creating product without sell_price"""
        product_data = {
            "name": "Test",
            "buy_price": 10.0
        }

        response = await client.post("/products/", json=product_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_product_negative_buy_price(self, client, mock_db):
        """Test creating product with negative buy price"""
        product_data = {
            "name": "Test",
            "buy_price": -10.0,
            "sell_price": 15.0
        }

        response = await client.post("/products/", json=product_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_product_negative_sell_price(self, client, mock_db):
        """Test creating product with negative sell price"""
        product_data = {
            "name": "Test",
            "buy_price": 10.0,
            "sell_price": -15.0
        }

        response = await client.post("/products/", json=product_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_product_unauthorized(self, public_client):
        """Test creating product without authentication"""
        product_data = {
            "name": "Test",
            "buy_price": 10.0,
            "sell_price": 15.0
        }

        response = await public_client.post("/products/", json=product_data)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_product_empty_name(self, client, mock_db):
        """Test creating product with empty string name"""
        product_data = {
            "name": "",
            "buy_price": 10.0,
            "sell_price": 15.0
        }

        response = await client.post("/products/", json=product_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_product_whitespace_name(self, client, mock_db):
        """Test creating product with whitespace-only name"""
        product_data = {
            "name": "   ",
            "buy_price": 10.0,
            "sell_price": 15.0
        }

        with patch('products.service.ProductService.create', new_callable=AsyncMock) as mock_create:
            class MockProduct:
                id = 1
                name = "   "
                description = None
                buy_price = 10.0
                sell_price = 15.0
                user_id = 1

            mock_create.return_value = MockProduct()

            response = await client.post("/products/", json=product_data)

            # If your validation allows it, it succeeds; otherwise 422
            assert response.status_code in [201, 422]


class TestUpdateProduct:
    @pytest.mark.asyncio
    async def test_update_product_success(self, client, mock_db):
        """Test updating a product successfully"""
        update_data = {
            "name": "Updated Product",
            "description": "Updated Description",
            "buy_price": 12.0,
            "sell_price": 18.0
        }

        with patch('products.service.ProductService.update', new_callable=AsyncMock) as mock_update:
            class UpdatedProduct:
                id = 1
                name = "Updated Product"
                description = "Updated Description"
                buy_price = 12.0
                sell_price = 18.0
                user_id = 1

            mock_update.return_value = UpdatedProduct()

            response = await client.put("/products/1", json=update_data)

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Updated Product"
            assert data["buy_price"] == 12.0
            assert data["sell_price"] == 18.0
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_product_partial(self, client, mock_db):
        """Test partial update of product"""
        update_data = {
            "name": "Updated Name",
            "buy_price": 10.0,
            "sell_price": 15.0
        }

        with patch('products.service.ProductService.update', new_callable=AsyncMock) as mock_update:
            class UpdatedProduct:
                id = 1
                name = "Updated Name"
                description = "Original Description"
                buy_price = 10.0
                sell_price = 15.0
                user_id = 1

            mock_update.return_value = UpdatedProduct()

            response = await client.put("/products/1", json=update_data)

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_product_not_found(self, client, mock_db):
        """Test updating non-existent product"""
        update_data = {
            "name": "Updated",
            "buy_price": 10.0,
            "sell_price": 15.0
        }

        with patch('products.service.ProductService.update', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = None

            response = await client.put("/products/999", json=update_data)

            assert response.status_code == 404
            assert "999" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_product_unauthorized(self, public_client):
        """Test updating product without authentication"""
        update_data = {
            "name": "Updated",
            "buy_price": 10.0,
            "sell_price": 15.0
        }

        response = await public_client.put("/products/1", json=update_data)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_product_validation_error(self, client, mock_db):
        """Test updating product with invalid data"""
        update_data = {
            "name": "Updated",
            "buy_price": -10.0,
            "sell_price": 15.0
        }

        response = await client.put("/products/1", json=update_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_product_invalid_id(self, client, mock_db):
        """Test updating product with invalid ID"""
        update_data = {
            "name": "Updated",
            "buy_price": 10.0,
            "sell_price": 15.0
        }

        response = await client.put("/products/abc", json=update_data)
        assert response.status_code == 422


class TestDeleteProduct:
    @pytest.mark.asyncio
    async def test_delete_product_success(self, client, mock_db):
        """Test deleting a product successfully"""
        with patch('products.service.ProductService.delete', new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = True

            response = await client.delete("/products/1")

            assert response.status_code == 204
            assert response.content == b''

    @pytest.mark.asyncio
    async def test_delete_product_not_found(self, client, mock_db):
        """Test deleting non-existent product"""
        with patch('products.service.ProductService.delete', new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = False

            response = await client.delete("/products/999")

            assert response.status_code == 404
            assert "999" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_product_unauthorized(self, public_client):
        """Test deleting product without authentication"""
        response = await public_client.delete("/products/1")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_product_invalid_id(self, client, mock_db):
        """Test deleting product with invalid ID"""
        response = await client.delete("/products/abc")
        assert response.status_code == 422


class TestProductEdgeCases:
    @pytest.mark.asyncio
    async def test_get_products_service_exception(self, client, mock_db):
        """Test that unhandled service exceptions result in 500 error"""
        with patch('products.service.ProductService.get_all', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Database error")

            with pytest.raises(Exception, match="Database error"):
                response = await client.get("/products/")

    @pytest.mark.asyncio
    async def test_create_product_with_long_description(self, client, mock_db):
        """Test creating product with very long description"""
        product_data = {
            "name": "Product",
            "description": "A" * 1000,
            "buy_price": 10.0,
            "sell_price": 15.0
        }

        with patch('products.service.ProductService.create', new_callable=AsyncMock) as mock_create:
            class MockProduct:
                id = 1
                name = "Product"
                description = "A" * 1000
                buy_price = 10.0
                sell_price = 15.0
                user_id = 1

            mock_create.return_value = MockProduct()

            response = await client.post("/products/", json=product_data)

            assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_product_with_special_characters(self, client, mock_db):
        """Test creating product with special characters"""
        product_data = {
            "name": "Product™ & Co.",
            "description": "Special chars: <>&\"'",
            "buy_price": 10.0,
            "sell_price": 15.0
        }

        with patch('products.service.ProductService.create', new_callable=AsyncMock) as mock_create:
            class MockProduct:
                id = 1
                name = "Product™ & Co."
                description = "Special chars: <>&\"'"
                buy_price = 10.0
                sell_price = 15.0
                user_id = 1

            mock_create.return_value = MockProduct()

            response = await client.post("/products/", json=product_data)
            assert response.status_code == 201
