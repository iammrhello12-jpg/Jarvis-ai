from fastapi.testclient import TestClient
from .main import app

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Shopkeeper Inventory API"}

def test_create_product():
    response = client.post(
        "/api/products/",
        json={"name": "Test Product", "description": "Testing", "price": 10.5, "stock_quantity": 100},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Test Product"

def test_read_products():
    response = client.get("/api/products/")
    assert response.status_code == 200
    assert len(response.json()) > 0
