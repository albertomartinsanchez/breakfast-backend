from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.database import init_db
from core.config import settings
from auth.router import router as auth_router
from products.router import router as products_router
from customers.router import router as customers_router
from sales.router import router as sales_router
from sales.router_delivery import router as delivery_router
from customers.router_analytics import router as customer_analytics_router
from products.router_analytics import router as product_analytics_router
from analytics.router import router as analytics_router
from public_orders.router import router as public_orders_router

# Import models to ensure they're registered with SQLAlchemy
from notifications.models import PushDevice  # noqa: F401

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(customers_router)
app.include_router(sales_router)
app.include_router(delivery_router)
app.include_router(customer_analytics_router)
app.include_router(product_analytics_router)
app.include_router(analytics_router)
app.include_router(public_orders_router)  # Public customer ordering

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.app_name}!", "version": settings.app_version, "docs": "/docs"}
