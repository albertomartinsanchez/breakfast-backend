#!/usr/bin/env python3
"""
Migration script to encrypt existing customer data.

This script:
1. Adds the name_index column if it doesn't exist
2. Encrypts existing plaintext data (name, address, phone)
3. Generates blind indexes for all names

Usage:
    python scripts/migrate_encryption.py

IMPORTANT:
- Back up your database before running this script
- Ensure ENCRYPTION_KEY is set in your .env file
- This script is idempotent (safe to run multiple times)
"""
import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from core.config import settings
from core.crypto import encrypt, decrypt, blind_index, is_encrypted, generate_key


async def check_encryption_key():
    """Verify encryption key is configured."""
    if not settings.encryption_key:
        print("\n" + "=" * 60)
        print("ERROR: ENCRYPTION_KEY not configured!")
        print("=" * 60)
        print("\nGenerate a key with:")
        print(f"  python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
        print("\nThen add to your .env file:")
        print("  ENCRYPTION_KEY=your-generated-key-here")
        print("=" * 60 + "\n")
        return False
    print(f"[OK] Encryption key configured")
    return True


async def add_name_index_column(engine):
    """Add name_index column if it doesn't exist."""
    is_sqlite = "sqlite" in settings.database_url

    async with engine.connect() as conn:
        # Check if column exists
        if is_sqlite:
            result = await conn.execute(text("PRAGMA table_info(customer)"))
            columns = [row[1] for row in result.fetchall()]
        else:
            # PostgreSQL
            result = await conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'customer'"
            ))
            columns = [row[0] for row in result.fetchall()]

        if 'name_index' not in columns:
            print("[MIGRATING] Adding name_index column...")
            await conn.execute(text("ALTER TABLE customer ADD COLUMN name_index VARCHAR"))
            await conn.commit()
            print("[OK] name_index column added")
        else:
            print("[OK] name_index column already exists")


async def migrate_customer_data(engine):
    """Encrypt existing customer data and generate blind indexes."""
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get all customers
        result = await session.execute(text("SELECT id, name, address, phone, name_index FROM customer"))
        customers = result.fetchall()

        if not customers:
            print("[OK] No customers to migrate")
            return

        print(f"[MIGRATING] Processing {len(customers)} customers...")

        migrated = 0
        skipped = 0

        for customer in customers:
            cust_id, name, address, phone, name_idx = customer
            updates = {}

            # Check and encrypt name
            if name and not is_encrypted(name):
                updates['name'] = encrypt(name)
                updates['name_index'] = blind_index(name)
                migrated += 1
            elif name and not name_idx:
                # Already encrypted but no index - decrypt to create index
                decrypted_name = decrypt(name)
                updates['name_index'] = blind_index(decrypted_name)

            # Check and encrypt address
            if address and not is_encrypted(address):
                updates['address'] = encrypt(address)

            # Check and encrypt phone
            if phone and not is_encrypted(phone):
                updates['phone'] = encrypt(phone)

            if updates:
                # Build UPDATE statement
                set_clauses = ", ".join(f"{k} = :{k}" for k in updates.keys())
                updates['id'] = cust_id
                await session.execute(
                    text(f"UPDATE customer SET {set_clauses} WHERE id = :id"),
                    updates
                )
            else:
                skipped += 1

        await session.commit()
        print(f"[OK] Migrated: {migrated}, Already encrypted: {skipped}")


async def verify_migration(engine):
    """Verify encryption is working correctly."""
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(text("SELECT id, name, name_index FROM customer LIMIT 1"))
        customer = result.fetchone()

        if customer:
            cust_id, name, name_idx = customer
            if is_encrypted(name):
                decrypted = decrypt(name)
                print(f"[OK] Verification: Customer {cust_id} name is encrypted")
                print(f"     Encrypted: {name[:50]}...")
                print(f"     Decrypted: {decrypted}")
                print(f"     Index: {name_idx[:20]}..." if name_idx else "     Index: None")
            else:
                print(f"[WARNING] Customer {cust_id} name is NOT encrypted: {name}")
        else:
            print("[OK] No customers to verify")


async def main():
    print("\n" + "=" * 60)
    print("Customer Data Encryption Migration")
    print("=" * 60 + "\n")

    # Check encryption key
    if not await check_encryption_key():
        sys.exit(1)

    # Create engine
    engine = create_async_engine(settings.database_url, echo=False)

    try:
        # Step 1: Add column
        await add_name_index_column(engine)

        # Step 2: Migrate data
        await migrate_customer_data(engine)

        # Step 3: Verify
        print("\n[VERIFYING] Checking migration...")
        await verify_migration(engine)

        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60 + "\n")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
