from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt, JWTError
import os
import secrets
from typing import Optional, Dict, Any, Union

from database import get_db, SuperAdmin, ApiToken

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token settings
SECRET_KEY: str = os.environ.get("SECRET_KEY", "supersecretkey123456789")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

# Security schemes
token_auth = HTTPBearer()
basic_auth = HTTPBasic()

def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: The plain text password to hash
        
    Returns:
        The hashed password
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        plain_password: The plain text password to verify
        hashed_password: The hashed password to check against
        
    Returns:
        True if the password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: The data to encode in the token
        
    Returns:
        The encoded JWT token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str) -> Optional[str]:
    """
    Verify a JWT access token.
    
    Args:
        token: The token to verify
        
    Returns:
        The username from the token if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None

def verify_api_token(
    credentials: HTTPAuthorizationCredentials = Depends(token_auth), 
    db: Session = Depends(get_db)
) -> str:
    """
    Verify an API token from the Authorization header.
    
    Args:
        credentials: The authorization credentials from the request
        db: The database session
        
    Returns:
        The verified token
        
    Raises:
        HTTPException: If the token is invalid
    """
    token = credentials.credentials
    
    # Check against stored tokens in database
    db_token = db.query(ApiToken).filter(ApiToken.token == token, ApiToken.is_active == True).first()
    
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token

def verify_superadmin(
    credentials: HTTPBasicCredentials = Depends(basic_auth), 
    db: Session = Depends(get_db)
) -> SuperAdmin:
    """
    Verify superadmin credentials from Basic authentication.
    
    Args:
        credentials: The basic auth credentials from the request
        db: The database session
        
    Returns:
        The superadmin object if credentials are valid
        
    Raises:
        HTTPException: If the credentials are invalid
    """
    # Check against superadmin credentials
    superadmin = db.query(SuperAdmin).filter(
        SuperAdmin.username == credentials.username, 
        SuperAdmin.is_active == True
    ).first()
    
    if not superadmin or not verify_password(credentials.password, superadmin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return superadmin

def generate_api_token() -> str:
    """
    Generate a secure random API token.
    
    Returns:
        A 32-byte hex-encoded random token
    """
    return secrets.token_hex(32) 