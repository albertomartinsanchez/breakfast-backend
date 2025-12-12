"""
Unit tests for product endpoints
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from models import Product


class TestGetProducts:
    """Tests for GET /products endpoint"""
    
    @pytest.mark.anyio("asyncio")    
    async def test_get_products_success(self, client, mock_product_list):
        """Test getting all products successfully"""
        with patch('crud.get_products', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_product_list
            
            response = await client.get("/products/")
            
            assert response.status_code == 200
            data = response.json()
            print('data:', data)
            assert len(data) == 2
    
    @pytest.mark.anyio("asyncio")    
    async def test_get_products_empty(self, client):
        """Test getting products when database is empty"""
        with patch('crud.get_products', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []
            
            response = await client.get("/products/")
            
            assert response.status_code == 200
            assert response.json() == []


class TestGetProduct:
    """Tests for GET /products/{product_id} endpoint"""
    
    @pytest.mark.anyio("asyncio")    
    async def test_get_product_success(self, client, mock_product):
        """Test getting a single product by ID"""
        with patch('crud.get_product_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_product
            
            response = await client.get("/products/1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
    
    @pytest.mark.anyio("asyncio")    
    async def test_get_product_not_found(self, client):
        """Test getting a non-existent product"""
        with patch('crud.get_product_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            
            response = await client.get("/products/999")
            
            assert response.status_code == 404


class TestCreateProduct:
    """Tests for POST /products endpoint"""
    
    @pytest.mark.anyio("asyncio")    
    async def test_create_product_success(self, client):
        """Test creating a product successfully"""
        product_data = {
            "name": "New Product",
            "description": "New Description",
            "buy_price": 10.0,
            "sell_price": 15.0
        }
        
        with patch('crud.create_product', new_callable=AsyncMock) as mock_create:
            mock_obj = Product(
                id=1,
                name=product_data["name"],
                description=product_data["description"],
                buy_price=product_data["buy_price"],
                sell_price=product_data["sell_price"]
            )
            mock_create.return_value = mock_obj
            
            response = await client.post("/products/", json=product_data)
            
            assert response.status_code == 201
            assert response.json() == {
                "id": 1,
                "name": "New Product",
                "description": "New Description",
                "buy_price": 10.0,
                "sell_price": 15.0
            }
    
    @pytest.mark.anyio("asyncio")    
    async def test_create_product_missing_name(self, client):
        """Test creating a product without name"""
        product_data = {
            "description": "Description",
            "buy_price": 10.0,
            "sell_price": 15.0
        }
        
        response = await client.post("/products/", json=product_data)
        
        assert response.status_code == 422
    
    @pytest.mark.anyio("asyncio")    
    async def test_create_product_negative_price(self, client):
        """Test creating a product with negative price"""
        product_data = {
            "name": "Product",
            "buy_price": -10.0,
            "sell_price": 15.0
        }
        
        response = await client.post("/products/", json=product_data)
        
        assert response.status_code == 422


class TestUpdateProduct:
    """Tests for PUT /products/{product_id} endpoint"""
    
    @pytest.mark.anyio("asyncio")    
    async def test_update_product_success(self, client):
        """Test updating a product successfully"""
        product_data = {
            "name": "Updated Product",
            "description": "Updated Description",
            "buy_price": 12.0,
            "sell_price": 18.0
        }
        
        with patch('crud.update_product', new_callable=AsyncMock) as mock_update:
            mock_obj = Product(
                id=5,
                name=product_data["name"],
                description=product_data["description"],
                buy_price=product_data["buy_price"],
                sell_price=product_data["sell_price"]
            )
            mock_update.return_value = mock_obj
            
            response = await client.put("/products/1", json=product_data)
            
            assert response.status_code == 200
            assert response.json() == {
                "id": 5,
                "name": "Updated Product",
                "description": "Updated Description",
                "buy_price": 12.0,
                "sell_price": 18.0
            }
    
    @pytest.mark.anyio("asyncio")    
    async def test_update_product_not_found(self, client):
        """Test updating a non-existent product"""
        product_data = {
            "name": "Updated",
            "buy_price": 12.0,
            "sell_price": 18.0
        }
        
        with patch('crud.update_product', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = None
            
            response = await client.put("/products/999", json=product_data)
            
            assert response.status_code == 404


class TestDeleteProduct:
    """Tests for DELETE /products/{product_id} endpoint"""
    
    @pytest.mark.anyio("asyncio")    
    async def test_delete_product_success(self, client):
        """Test deleting a product successfully"""
        with patch('crud.delete_product', new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = True
            
            response = await client.delete("/products/1")
            
            assert response.status_code == 204
    
    @pytest.mark.anyio("asyncio")    
    async def test_delete_product_not_found(self, client):
        """Test deleting a non-existent product"""
        with patch('crud.delete_product', new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = False
            
            response = await client.delete("/products/999")
            
            assert response.status_code == 404
