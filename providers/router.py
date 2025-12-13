from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from core.database import get_db
from auth.dependencies import get_current_user
from providers import crud, schemas

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/", response_model=List[schemas.ProviderResponse])
async def get_providers(db: AsyncSession = Depends(get_db), current_user: str = Depends(get_current_user)):
    return await crud.get_providers(db)


@router.get("/{provider_id}", response_model=schemas.ProviderResponse)
async def get_provider(provider_id: int, db: AsyncSession = Depends(get_db), current_user: str = Depends(get_current_user)):
    provider = await crud.get_provider_by_id(db, provider_id)
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Provider with id {provider_id} not found")
    return provider


@router.post("/", response_model=schemas.ProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(provider_in: schemas.ProviderCreate, db: AsyncSession = Depends(get_db), current_user: str = Depends(get_current_user)):
    existing = await crud.get_provider_by_email(db, provider_in.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provider with this email already exists")
    return await crud.create_provider(db, provider_in)


@router.put("/{provider_id}", response_model=schemas.ProviderResponse)
async def update_provider(provider_id: int, provider_in: schemas.ProviderUpdate, db: AsyncSession = Depends(get_db), current_user: str = Depends(get_current_user)):
    existing = await crud.get_provider_by_email(db, provider_in.email)
    if existing and existing.id != provider_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provider with this email already exists")
    
    provider = await crud.update_provider(db, provider_id, provider_in)
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Provider with id {provider_id} not found")
    return provider


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(provider_id: int, db: AsyncSession = Depends(get_db), current_user: str = Depends(get_current_user)):
    deleted = await crud.delete_provider(db, provider_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Provider with id {provider_id} not found")
    return None
