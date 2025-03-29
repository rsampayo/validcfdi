from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt, JWTError
import os
import secrets

from database import get_db, SuperAdmin, ApiToken

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token settings
SECRET_KEY = os.environ.get("SECRET_KEY", "supersecretkey123456789")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security schemes
token_auth = HTTPBearer()
basic_auth = HTTPBasic()

# Password hashing functions
def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# JWT token functions
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None

# Verify token for regular API access
def verify_api_token(credentials: HTTPAuthorizationCredentials = Depends(token_auth), db: Session = Depends(get_db)):
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

# Verify superadmin credentials
def verify_superadmin(credentials: HTTPBasicCredentials = Depends(basic_auth), db: Session = Depends(get_db)):
    # Check against superadmin credentials
    superadmin = db.query(SuperAdmin).filter(SuperAdmin.username == credentials.username, SuperAdmin.is_active == True).first()
    
    if not superadmin or not verify_password(credentials.password, superadmin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return superadmin

# Function to generate a new API token
def generate_api_token():
    return secrets.token_hex(32) 