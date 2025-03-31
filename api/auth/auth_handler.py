"""
Authentication handlers for the API

Provides functions for API token validation and admin authentication.
"""
from fastapi import HTTPException, status, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import base64
import binascii
import os

# Set up bearer token authentication
token_auth = HTTPBearer()

# Default API token (for development only)
DEFAULT_API_TOKEN = os.getenv("DEFAULT_API_TOKEN", "your-secret-token")

async def validate_api_token(credentials: HTTPAuthorizationCredentials = Depends(token_auth)):
    """
    Validate API token for endpoints that require authentication
    
    Args:
        credentials: Bearer token credentials
        
    Returns:
        The validated token
        
    Raises:
        HTTPException: If the token is invalid
    """
    token = credentials.credentials
    
    # For now, we're just using a single token for simplicity
    # In a real application, you'd validate the token against a database
    if token != DEFAULT_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API token"
        )
    
    return token

async def validate_admin_credentials(authorization: str = Header(None)):
    """
    Validate admin credentials using Basic Auth
    
    Args:
        authorization: Basic auth credentials
        
    Returns:
        The validated admin username
        
    Raises:
        HTTPException: If the credentials are invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    try:
        # Check if it starts with "Basic "
        if not authorization.startswith("Basic "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication method",
                headers={"WWW-Authenticate": "Basic"},
            )
        
        # Get the base64 encoded credentials
        auth_base64 = authorization.split("Basic ")[1]
        
        # Decode the base64 credentials
        credentials = base64.b64decode(auth_base64).decode("utf-8")
        
        # Split username and password
        username, password = credentials.split(":", 1)
        
        # For now, we're just using hardcoded credentials for simplicity
        # In a real application, you'd validate against a database
        expected_username = os.getenv("SUPERADMIN_USERNAME", "admin")
        expected_password = os.getenv("SUPERADMIN_PASSWORD", "caragram")
        
        if username != expected_username or password != expected_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
        
        return username
    except binascii.Error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Basic"},
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials format",
            headers={"WWW-Authenticate": "Basic"},
        ) 