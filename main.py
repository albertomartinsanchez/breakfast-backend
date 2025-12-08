from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import secrets
from datetime import datetime, timedelta

app = FastAPI(title="My API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Data models
class Product(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    buy_price: float
    sell_price: float

class User(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# In-memory databases
products_db = []
next_id = 1

# Simulated users database (in production, use hashed passwords!)
users_db = {
    "admin": "secret123",
    "user": "pass456"
}

# Active tokens storage
active_tokens = {}

def create_token(username: str) -> str:
    """Generate a new access token"""
    token = secrets.token_urlsafe(32)
    active_tokens[token] = {
        "username": username,
        "expires": datetime.now() + timedelta(hours=24)
    }
    return token

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify the access token"""
    token = credentials.credentials
    
    if token not in active_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    token_data = active_tokens[token]
    
    if datetime.now() > token_data["expires"]:
        del active_tokens[token]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    
    return token_data["username"]

@app.get("/")
def read_root():
    return {"message": "Welcome to my FastAPI! Use /login to authenticate."}

@app.post("/login", response_model=Token)
def login(user: User):
    """Login and get access token"""
    if user.username not in users_db or users_db[user.username] != user.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    token = create_token(user.username)
    return {"access_token": token, "token_type": "bearer"}

@app.post("/logout")
def logout(username: str = Depends(verify_token)):
    """Logout and invalidate token"""
    # Remove all tokens for this user
    tokens_to_remove = [t for t, data in active_tokens.items() if data["username"] == username]
    for token in tokens_to_remove:
        del active_tokens[token]
    return {"message": "Logged out successfully"}

@app.get("/products", response_model=List[Product])
def get_products(username: str = Depends(verify_token)):
    """Get all products (requires authentication)"""
    return products_db

@app.get("/products/{product_id}", response_model=Product)
def get_product(product_id: int, username: str = Depends(verify_token)):
    """Get a specific product by ID (requires authentication)"""
    for product in products_db:
        if product.id == product_id:
            return product
    raise HTTPException(status_code=404, detail="Product not found")

@app.post("/products", response_model=Product, status_code=201)
def create_product(product: Product, username: str = Depends(verify_token)):
    """Create a new product (requires authentication)"""
    global next_id
    product.id = next_id
    next_id += 1
    products_db.append(product)
    return product

@app.put("/products/{product_id}", response_model=Product)
def update_product(product_id: int, updated_product: Product, username: str = Depends(verify_token)):
    """Update an existing product (requires authentication)"""
    for i, product in enumerate(products_db):
        if product.id == product_id:
            updated_product.id = product_id
            products_db[i] = updated_product
            return updated_product
    raise HTTPException(status_code=404, detail="Product not found")

@app.delete("/products/{product_id}")
def delete_product(product_id: int, username: str = Depends(verify_token)):
    """Delete a product (requires authentication)"""
    for i, product in enumerate(products_db):
        if product.id == product_id:
            products_db.pop(i)
            return {"message": "Product deleted successfully"}
    raise HTTPException(status_code=404, detail="Product not found")

# Run with: python -m uvicorn main:app --reload