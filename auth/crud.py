from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from auth.models import User
from auth.schemas import UserSignup
from core.security import get_password_hash

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()

async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, user_in: UserSignup) -> User:
    db_user = User(email=user_in.email, hashed_password=get_password_hash(user_in.password))
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user
