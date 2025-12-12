import pytest

class TestRoot:

    @pytest.mark.anyio 
    async def test_root_no_auth_required(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data
        assert data["docs"] == "/docs"
