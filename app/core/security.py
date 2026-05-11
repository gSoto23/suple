from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

from cryptography.fernet import Fernet
import logging

def encrypt_value(value: str) -> Optional[str]:
    if not value:
        return None
    if not settings.ENCRYPTION_KEY:
        logging.warning("ENCRYPTION_KEY is not set. Storing value unencrypted.")
        return value
    try:
        f = Fernet(settings.ENCRYPTION_KEY.encode())
        return f.encrypt(value.encode()).decode()
    except Exception as e:
        logging.error(f"Encryption failed: {e}")
        return value

def decrypt_value(encrypted_value: str) -> Optional[str]:
    if not encrypted_value:
        return None
    if not settings.ENCRYPTION_KEY:
        return encrypted_value
    try:
        f = Fernet(settings.ENCRYPTION_KEY.encode())
        return f.decrypt(encrypted_value.encode()).decode()
    except Exception as e:
        # If it fails to decrypt, it might be an old unencrypted value
        return encrypted_value
