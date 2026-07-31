"""
Jarvis OS - Security Manager

Handles Role-Based Access Control (RBAC) and Encryption of API Keys.
"""
from cryptography.fernet import Fernet
import os
from typing import Optional
from fastapi import HTTPException, status

# In a real app, this should be generated and stored securely (e.g., in .env)
# Fernet.generate_key()
raw_key = os.environ.get("JARVIS_SECRET_KEY", "MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI=")
if isinstance(raw_key, str):
    raw_key = raw_key.strip()
SECRET_KEY = raw_key.encode() if isinstance(raw_key, str) else raw_key

class SecurityManager:
    def __init__(self):
        self.cipher_suite = Fernet(SECRET_KEY)

    def encrypt_key(self, plain_text_key: str) -> str:
        """Encrypts an API key for safe database storage."""
        if not plain_text_key:
            return ""
        return self.cipher_suite.encrypt(plain_text_key.encode()).decode()

    def decrypt_key(self, encrypted_key: str) -> str:
        """Decrypts an API key for usage."""
        if not encrypted_key:
            return ""
        return self.cipher_suite.decrypt(encrypted_key.encode()).decode()

    def verify_role(self, user_role: str, required_role: str) -> bool:
        """Verifies if the user has the required role."""
        roles = ["viewer", "user", "admin"]
        try:
            user_level = roles.index(user_role)
            required_level = roles.index(required_role)
            return user_level >= required_level
        except ValueError:
            return False

    def require_role(self, required_role: str):
        """Dependency for FastAPI routes to enforce RBAC."""
        def role_checker(user_role: str):
            if not self.verify_role(user_role, required_role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            return user_role
        return role_checker

security_manager = SecurityManager()
