class TestLogin:
    def test_login_success(self, client):
        response = client.post("/auth/login", json={"username": "admin", "password": "secret123"})
        assert response.status_code == 200
        assert "access_token" in response.json()
    
    def test_login_invalid(self, client):
        response = client.post("/auth/login", json={"username": "wrong", "password": "wrong"})
        assert response.status_code == 401
