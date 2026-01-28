"""
SQLAlchemy TypeDecorator for transparent field-level encryption.

Usage:
    from core.encrypted_type import EncryptedString

    class Customer(Base):
        name = Column(EncryptedString, nullable=False)
        address = Column(EncryptedString)
"""
from sqlalchemy import String, TypeDecorator
from core.crypto import encrypt, decrypt


class EncryptedString(TypeDecorator):
    """
    SQLAlchemy type that transparently encrypts/decrypts string values.

    Data is encrypted when written to the database and decrypted when read.
    Uses Fernet encryption (AES-128-CBC + HMAC-SHA256).
    """
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Encrypt value before storing in database."""
        if value is None:
            return None
        return encrypt(value)

    def process_result_value(self, value, dialect):
        """Decrypt value when reading from database."""
        if value is None:
            return None
        return decrypt(value)
