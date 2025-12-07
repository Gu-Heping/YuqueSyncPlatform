from datetime import datetime, timedelta
from typing import Optional, Union, Any
from jose import jwt
from app.core.config import settings
import hashlib
import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Pre-hash with SHA256 to avoid bcrypt 72-byte limit
    digest = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
    # bcrypt.checkpw expects bytes
    return bcrypt.checkpw(digest.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    # Pre-hash with SHA256 to avoid bcrypt 72-byte limit
    digest = hashlib.sha256(password.encode('utf-8')).hexdigest()
    # bcrypt.hashpw expects bytes and returns bytes
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(digest.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
