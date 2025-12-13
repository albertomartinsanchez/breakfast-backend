from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from providers.models import Provider
from providers.schemas import ProviderCreate, ProviderUpdate


async def get_providers(db: AsyncSession) -> List[Provider]:
    result = await db.execute(select(Provider))
    return result.scalars().all()


async def get_provider_by_id(db: AsyncSession, provider_id: int) -> Optional[Provider]:
    result = await db.execute(select(Provider).where(Provider.id == provider_id))
    return result.scalar_one_or_none()


async def get_provider_by_email(db: AsyncSession, email: str) -> Optional[Provider]:
    result = await db.execute(select(Provider).where(Provider.email == email))
    return result.scalar_one_or_none()


async def create_provider(db: AsyncSession, provider_in: ProviderCreate) -> Provider:
    db_provider = Provider(
        name=provider_in.name,
        email=provider_in.email,
        phone=provider_in.phone,
        address=provider_in.address
    )
    db.add(db_provider)
    await db.commit()
    await db.refresh(db_provider)
    return db_provider


async def update_provider(db: AsyncSession, provider_id: int, provider_in: ProviderUpdate) -> Optional[Provider]:
    db_provider = await get_provider_by_id(db, provider_id)
    if not db_provider:
        return None
    
    db_provider.name = provider_in.name
    db_provider.email = provider_in.email
    db_provider.phone = provider_in.phone
    db_provider.address = provider_in.address
    
    await db.commit()
    await db.refresh(db_provider)
    return db_provider


async def delete_provider(db: AsyncSession, provider_id: int) -> bool:
    db_provider = await get_provider_by_id(db, provider_id)
    if not db_provider:
        return False
    
    await db.delete(db_provider)
    await db.commit()
    return True
