from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import uuid
from customers.models import Customer
from customers.models_access_token import CustomerAccessToken
from customers.schemas import CustomerCreate, CustomerUpdate
from core.crypto import blind_index

async def get_customers(db: AsyncSession, user_id: int) -> List[Customer]:
    result = await db.execute(
        select(Customer)
        .where(Customer.user_id == user_id)
        .options(selectinload(Customer.access_token))
    )
    return result.scalars().all()

async def get_customer_by_id(db: AsyncSession, customer_id: int, user_id: int) -> Optional[Customer]:
    result = await db.execute(
        select(Customer)
        .where(Customer.id == customer_id, Customer.user_id == user_id)
        .options(selectinload(Customer.access_token))
    )
    return result.scalar_one_or_none()

async def create_customer(db: AsyncSession, customer_in: CustomerCreate, user_id: int) -> Customer:
    # Create customer with encrypted fields and blind index
    db_customer = Customer(
        user_id=user_id,
        name=customer_in.name,
        address=customer_in.address,
        phone=customer_in.phone,
        name_index=blind_index(customer_in.name),
        credit=customer_in.credit or 0.0
    )
    db.add(db_customer)
    await db.flush()
    
    # Auto-generate access token
    token = CustomerAccessToken(
        customer_id=db_customer.id,
        access_token=str(uuid.uuid4())
    )
    db.add(token)
    
    await db.commit()
    await db.refresh(db_customer, ["access_token"])
    return db_customer

async def update_customer(db: AsyncSession, customer_id: int, customer_in: CustomerUpdate, user_id: int) -> Optional[Customer]:
    db_customer = await get_customer_by_id(db, customer_id, user_id)
    if not db_customer:
        return None
    db_customer.name = customer_in.name
    db_customer.address = customer_in.address
    db_customer.phone = customer_in.phone
    db_customer.name_index = blind_index(customer_in.name)
    if customer_in.credit is not None:
        db_customer.credit = customer_in.credit
    await db.commit()
    await db.refresh(db_customer)
    return db_customer

async def delete_customer(db: AsyncSession, customer_id: int, user_id: int) -> bool:
    db_customer = await get_customer_by_id(db, customer_id, user_id)
    if not db_customer:
        return False
    await db.delete(db_customer)
    await db.commit()
    return True
