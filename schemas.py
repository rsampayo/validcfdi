from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Token schemas
class TokenBase(BaseModel):
    description: Optional[str] = Field(None, description="Description of the token's purpose")

class TokenCreate(TokenBase):
    pass

class TokenUpdate(BaseModel):
    description: Optional[str] = Field(None, description="Description of the token's purpose")
    is_active: Optional[bool] = Field(None, description="Whether the token is active")

class TokenResponse(TokenBase):
    id: int
    token: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TokenList(BaseModel):
    tokens: List[TokenResponse]
    total: int

# Superadmin schemas
class SuperAdminCreate(BaseModel):
    username: str = Field(..., description="Username for the superadmin")
    password: str = Field(..., description="Password for the superadmin")

class SuperAdminUpdate(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., description="New password")

class SuperAdminResponse(BaseModel):
    username: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Message response
class MessageResponse(BaseModel):
    message: str 