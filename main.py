from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import secrets
from datetime import datetime, timedelta
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import Column, Integer, String, Float, select
from sqlalchemy.ext.declarative import declarative_base

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

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./products.db")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# Database Models
class ProductDB(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    buy_price = Column(Float, nullable=False)
    sell_price = Column(Float, nullable=False)

# Create tables on startup
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Pydantic models
class Product(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    buy_price: float
    sell_price: float
    
    class Config:
        from_attributes = True

class User(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# Simulated users database (in production, use hashed passwords!)
users_db = {
    "admin": "secret123",
    "user": "pass456"
}

# Active tokens storage
active_tokens = {}

# Database dependency
async def get_db():
    async with async_session_maker() as session:
        yield session

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
async def read_root():
    return {"message": "Welcome to my FastAPI! Use /login to authenticate."}

@app.post("/login", response_model=Token)
async def login(user: User):
    """Login and get access token"""
    if user.username not in users_db or users_db[user.username] != user.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    token = create_token(user.username)
    return {"access_token": token, "token_type": "bearer"}

@app.post("/logout")
async def logout(username: str = Depends(verify_token)):
    """Logout and invalidate token"""
    tokens_to_remove = [t for t, data in active_tokens.items() if data["username"] == username]
    for token in tokens_to_remove:
        del active_tokens[token]
    return {"message": "Logged out successfully"}

@app.get("/products", response_model=List[Product])
async def get_products(username: str = Depends(verify_token), db: AsyncSession = Depends(get_db)):
    """Get all products (requires authentication)"""
    result = await db.execute(select(ProductDB))
    products = result.scalars().all()
    return products

@app.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: int, username: str = Depends(verify_token), db: AsyncSession = Depends(get_db)):
    """Get a specific product by ID (requires authentication)"""
    result = await db.execute(select(ProductDB).where(ProductDB.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.post("/products", response_model=Product, status_code=201)
async def create_product(product: Product, username: str = Depends(verify_token), db: AsyncSession = Depends(get_db)):
    """Create a new product (requires authentication)"""
    db_product = ProductDB(
        name=product.name,
        description=product.description,
        buy_price=product.buy_price,
        sell_price=product.sell_price
    )
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product

@app.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: int, product: Product, username: str = Depends(verify_token), db: AsyncSession = Depends(get_db)):
    """Update an existing product (requires authentication)"""
    result = await db.execute(select(ProductDB).where(ProductDB.id == product_id))
    db_product = result.scalar_one_or_none()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db_product.name = product.name
    db_product.description = product.description
    db_product.buy_price = product.buy_price
    db_product.sell_price = product.sell_price
    
    await db.commit()
    await db.refresh(db_product)
    return db_product

@app.delete("/products/{product_id}")
async def delete_product(product_id: int, username: str = Depends(verify_token), db: AsyncSession = Depends(get_db)):
    """Delete a product (requires authentication)"""
    result = await db.execute(select(ProductDB).where(ProductDB.id == product_id))
    db_product = result.scalar_one_or_none()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    await db.delete(db_product)
    await db.commit()
    return {"message": "Product deleted successfully"}

# Run with: python -m uvicorn main:app --reload