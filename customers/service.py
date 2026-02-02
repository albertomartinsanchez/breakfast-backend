from typing import List, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from customers.models import Customer
from customers.models_access_token import CustomerAccessToken
from customers.repository import CustomerRepository, CustomerAccessTokenRepository
from customers.schemas import CustomerCreate, CustomerUpdate
from core.crypto import blind_index


class CustomerService:
    """
    Service layer for Customer business logic.

    This class orchestrates operations using repositories and contains
    all business logic such as validation, access token generation, etc.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.customer_repo = CustomerRepository(db)
        self.token_repo = CustomerAccessTokenRepository(db)

    async def get_all(self, user_id: int) -> List[Customer]:
        """Get all customers for a user."""
        return await self.customer_repo.get_all(user_id)

    async def get_by_id(self, customer_id: int, user_id: int) -> Optional[Customer]:
        """Get a customer by ID."""
        return await self.customer_repo.get_by_id(customer_id, user_id)

    async def create(self, customer_in: CustomerCreate, user_id: int) -> Customer:
        """
        Create a new customer with auto-generated access token.

        Business logic:
        - Generate blind index for searchable name
        - Auto-generate access token for customer portal
        """
        customer = Customer(
            user_id=user_id,
            name=customer_in.name,
            address=customer_in.address,
            phone=customer_in.phone,
            name_index=blind_index(customer_in.name),
            credit=customer_in.credit or 0.0
        )

        await self.customer_repo.add(customer)
        await self.customer_repo.flush()

        token = CustomerAccessToken(
            customer_id=customer.id,
            access_token=self._generate_access_token()
        )
        await self.token_repo.add(token)

        await self.customer_repo.commit()
        await self.customer_repo.refresh(customer, ["access_token"])

        return customer

    async def update(
        self, customer_id: int, customer_in: CustomerUpdate, user_id: int
    ) -> Optional[Customer]:
        """
        Update an existing customer.

        Business logic:
        - Regenerate blind index when name changes
        """
        customer = await self.customer_repo.get_by_id(customer_id, user_id)
        if not customer:
            return None

        customer.name = customer_in.name
        customer.address = customer_in.address
        customer.phone = customer_in.phone
        customer.name_index = blind_index(customer_in.name)

        if customer_in.credit is not None:
            customer.credit = customer_in.credit

        await self.customer_repo.commit()
        await self.customer_repo.refresh(customer)

        return customer

    async def delete(self, customer_id: int, user_id: int) -> bool:
        """Delete a customer."""
        customer = await self.customer_repo.get_by_id(customer_id, user_id)
        if not customer:
            return False

        await self.customer_repo.delete(customer)
        await self.customer_repo.commit()

        return True

    def _generate_access_token(self) -> str:
        """Generate a unique access token."""
        return str(uuid.uuid4())
