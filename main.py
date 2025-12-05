from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional
import secrets
from datetime import datetime, timedelta

app = FastAPI(title="My API", version="1.0.0")
security = HTTPBearer()

# Data models
class Item(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float

class User(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# In-memory databases
items_db = []
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

@app.get("/items", response_model=List[Item])
def get_items(username: str = Depends(verify_token)):
    """Get all items (requires authentication)"""
    return items_db

@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: int, username: str = Depends(verify_token)):
    """Get a specific item by ID (requires authentication)"""
    for item in items_db:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")

@app.post("/items", response_model=Item, status_code=201)
def create_item(item: Item, username: str = Depends(verify_token)):
    """Create a new item (requires authentication)"""
    global next_id
    item.id = next_id
    next_id += 1
    items_db.append(item)
    return item

@app.put("/items/{item_id}", response_model=Item)
def update_item(item_id: int, updated_item: Item, username: str = Depends(verify_token)):
    """Update an existing item (requires authentication)"""
    for i, item in enumerate(items_db):
        if item.id == item_id:
            updated_item.id = item_id
            items_db[i] = updated_item
            return updated_item
    raise HTTPException(status_code=404, detail="Item not found")

@app.delete("/items/{item_id}")
def delete_item(item_id: int, username: str = Depends(verify_token)):
    """Delete an item (requires authentication)"""
    for i, item in enumerate(items_db):
        if item.id == item_id:
            items_db.pop(i)
            return {"message": "Item deleted successfully"}
    raise HTTPException(status_code=404, detail="Item not found")

# Run with: python -m uvicorn main:app --reload
