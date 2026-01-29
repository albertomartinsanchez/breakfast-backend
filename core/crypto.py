"""
Encryption service for sensitive data using Fernet (AES-128-CBC + HMAC-SHA256).

Usage:
    from core.crypto import encrypt, decrypt, blind_index

    # Encrypt sensitive data
    ciphertext = encrypt("John Doe")

    # Decrypt data
    plaintext = decrypt(ciphertext)

    # Create blind index for searchable encryption
    index = blind_index("John Doe")
"""
import hashlib
import hmac
import logging
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_fernet: Optional[Fernet] = None
_key_bytes: Optional[bytes] = None


def _get_fernet() -> Optional[Fernet]:
    """Lazily initialize Fernet cipher with encryption key."""
    global _fernet, _key_bytes

    if _fernet is not None:
        return _fernet

    from core.config import settings

    if not settings.encryption_key:
        logger.warning("ENCRYPTION_KEY not configured - data will NOT be encrypted")
        return None

    try:
        _key_bytes = settings.encryption_key.encode()
        _fernet = Fernet(_key_bytes)
        logger.info("Encryption service initialized successfully")
        return _fernet
    except Exception as e:
        logger.error(f"Failed to initialize encryption: {e}")
        return None


def generate_key() -> str:
    """Generate a new Fernet encryption key."""
    return Fernet.generate_key().decode()


def encrypt(plaintext: Optional[str]) -> Optional[str]:
    """
    Encrypt a string using Fernet.

    Args:
        plaintext: The string to encrypt

    Returns:
        Base64-encoded ciphertext, or original value if encryption not configured
    """
    if plaintext is None:
        return None

    fernet = _get_fernet()
    if fernet is None:
        return plaintext

    try:
        ciphertext = fernet.encrypt(plaintext.encode())
        return ciphertext.decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return plaintext


def decrypt(ciphertext: Optional[str]) -> Optional[str]:
    """
    Decrypt a Fernet-encrypted string.

    Args:
        ciphertext: The base64-encoded ciphertext

    Returns:
        Decrypted plaintext, or original value if decryption fails
    """
    if ciphertext is None:
        return None

    fernet = _get_fernet()
    if fernet is None:
        return ciphertext

    try:
        plaintext = fernet.decrypt(ciphertext.encode())
        return plaintext.decode()
    except InvalidToken:
        # Data might not be encrypted (legacy data)
        logger.debug("Decryption failed - data may be unencrypted")
        return ciphertext
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return ciphertext


def blind_index(value: Optional[str]) -> Optional[str]:
    """
    Create a blind index for searchable encryption.

    Uses HMAC-SHA256 with the encryption key to create a deterministic
    but non-reversible index that allows exact-match searches.

    Args:
        value: The value to index (will be lowercased and stripped)

    Returns:
        Hex-encoded HMAC, or None if value is None
    """
    if value is None:
        return None

    from core.config import settings

    if not settings.encryption_key:
        # No encryption configured, return normalized value
        return value.lower().strip()

    # Normalize value for consistent indexing
    normalized = value.lower().strip()

    # Create HMAC using encryption key
    key = settings.encryption_key.encode()
    h = hmac.new(key, normalized.encode(), hashlib.sha256)
    return h.hexdigest()


def is_encrypted(value: Optional[str]) -> bool:
    """
    Check if a value appears to be Fernet-encrypted.

    Fernet tokens start with 'gAAAAA' (base64-encoded version byte).
    """
    if value is None:
        return False
    return value.startswith('gAAAAA')
