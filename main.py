from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.database import init_db
from core.config import settings
from auth.router import router as auth_router
from products.router import router as products_router
from customers.router import router as customers_router
from sales.router import router as sales_router

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

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.app_name}!", "version": settings.app_version, "docs": "/docs"}
