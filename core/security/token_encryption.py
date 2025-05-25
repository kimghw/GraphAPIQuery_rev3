"""Token encryption and decryption utilities."""

import base64
import secrets
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from core.exceptions import ConfigurationException, SystemException


class TokenEncryption:
    """Token encryption and decryption service."""
    
    def __init__(self, encryption_key: str, salt: Optional[str] = None):
        """
        Initialize token encryption.
        
        Args:
            encryption_key: Base encryption key
            salt: Optional salt for key derivation (auto-generated if not provided)
        """
        if not encryption_key:
            raise ConfigurationException(
                "ENCRYPTION_KEY", 
                "Encryption key cannot be empty"
            )
        
        self.salt = salt.encode() if salt else secrets.token_bytes(16)
        self.fernet = self._create_fernet(encryption_key)
    
    def _create_fernet(self, encryption_key: str) -> Fernet:
        """Create Fernet instance with derived key."""
        try:
            # Derive key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self.salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(encryption_key.encode()))
            return Fernet(key)
        except Exception as e:
            raise ConfigurationException(
                "ENCRYPTION_KEY", 
                f"Failed to create encryption key: {str(e)}"
            )
    
    def encrypt_token(self, token: str) -> str:
        """
        Encrypt a token.
        
        Args:
            token: Plain text token to encrypt
            
        Returns:
            Encrypted token as base64 string
            
        Raises:
            SystemException: If encryption fails
        """
        if not token:
            return ""
        
        try:
            encrypted_bytes = self.fernet.encrypt(token.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
        except Exception as e:
            raise SystemException(
                "ENCRYPTION_ERROR",
                f"Failed to encrypt token: {str(e)}"
            )
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """
        Decrypt a token.
        
        Args:
            encrypted_token: Encrypted token as base64 string
            
        Returns:
            Decrypted plain text token
            
        Raises:
            SystemException: If decryption fails
        """
        if not encrypted_token:
            return ""
        
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_token.encode())
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            raise SystemException(
                "DECRYPTION_ERROR",
                f"Failed to decrypt token: {str(e)}"
            )
    
    def is_encrypted(self, token: str) -> bool:
        """
        Check if a token appears to be encrypted.
        
        Args:
            token: Token to check
            
        Returns:
            True if token appears encrypted, False otherwise
        """
        if not token:
            return False
        
        try:
            # Try to decode as base64
            base64.urlsafe_b64decode(token.encode())
            # If successful and contains encrypted-like patterns, likely encrypted
            return len(token) > 100 and '=' in token
        except Exception:
            return False
    
    @staticmethod
    def generate_encryption_key() -> str:
        """
        Generate a new encryption key.
        
        Returns:
            Base64-encoded encryption key
        """
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    
    def get_salt_b64(self) -> str:
        """
        Get the salt as base64 string.
        
        Returns:
            Base64-encoded salt
        """
        return base64.urlsafe_b64encode(self.salt).decode()


class TokenEncryptionFactory:
    """Factory for creating token encryption instances."""
    
    _instance: Optional[TokenEncryption] = None
    
    @classmethod
    def create(
        self, 
        encryption_key: str, 
        salt: Optional[str] = None
    ) -> TokenEncryption:
        """
        Create or get token encryption instance.
        
        Args:
            encryption_key: Base encryption key
            salt: Optional salt for key derivation
            
        Returns:
            TokenEncryption instance
        """
        if not self._instance:
            self._instance = TokenEncryption(encryption_key, salt)
        return self._instance
    
    @classmethod
    def reset(cls):
        """Reset the singleton instance."""
        cls._instance = None


def create_token_encryption(
    encryption_key: str, 
    salt: Optional[str] = None
) -> TokenEncryption:
    """
    Create token encryption instance.
    
    Args:
        encryption_key: Base encryption key
        salt: Optional salt for key derivation
        
    Returns:
        TokenEncryption instance
    """
    return TokenEncryptionFactory.create(encryption_key, salt)
