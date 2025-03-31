from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# Token schemas
class TokenBase(BaseModel):
    """Base schema for token data with common fields."""
    description: Optional[str] = Field(None, description="Description of the token's purpose")

class TokenCreate(TokenBase):
    """Schema for creating a new token."""
    pass

class TokenUpdate(BaseModel):
    """Schema for updating an existing token."""
    description: Optional[str] = Field(None, description="Description of the token's purpose")
    is_active: Optional[bool] = Field(None, description="Whether the token is active")

class TokenResponse(TokenBase):
    """Schema for token data in responses."""
    id: int = Field(..., description="Unique identifier for the token")
    token: str = Field(..., description="The token value")
    is_active: bool = Field(..., description="Whether the token is active")
    created_at: datetime = Field(..., description="When the token was created")
    updated_at: datetime = Field(..., description="When the token was last updated")
    
    class Config:
        from_attributes = True

class TokenList(BaseModel):
    """Schema for a list of tokens."""
    tokens: List[TokenResponse] = Field(..., description="List of token objects")
    total: int = Field(..., description="Total number of tokens")

# Superadmin schemas
class SuperAdminCreate(BaseModel):
    """Schema for creating a new superadmin."""
    username: str = Field(..., description="Username for the superadmin")
    password: str = Field(..., description="Password for the superadmin")

class SuperAdminUpdate(BaseModel):
    """Schema for updating a superadmin password."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., description="New password")

class SuperAdminResponse(BaseModel):
    """Schema for superadmin data in responses."""
    username: str = Field(..., description="Username of the superadmin")
    is_active: bool = Field(..., description="Whether the superadmin account is active")
    created_at: datetime = Field(..., description="When the superadmin account was created")
    
    class Config:
        from_attributes = True

# Message response
class MessageResponse(BaseModel):
    """Schema for simple message responses."""
    message: str = Field(..., description="Response message") 