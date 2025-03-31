"""
Admin Routes

API endpoints for administrative tasks.
"""
from fastapi import APIRouter, HTTPException, Depends, Body, BackgroundTasks, Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from api.auth.auth_handler import validate_admin_credentials
from api.services.token_service import (
    create_token, 
    get_tokens, 
    get_token_by_id, 
    update_token, 
    delete_token, 
    regenerate_token
)
from api.services.admin_service import (
    create_admin, 
    update_admin_password, 
    deactivate_admin
)
from api.services.efos_verification import get_efos_metadata, update_efos_database

# Create router
router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(validate_admin_credentials)],
)

# Models
class TokenCreate(BaseModel):
    """Request model for token creation"""
    description: str = Field(..., description="Description of the token")
    
class TokenResponse(BaseModel):
    """Response model for token operations"""
    id: int
    token: str
    description: str
    created_at: Optional[str] = None
    last_used_at: Optional[str] = None
    
class TokenUpdate(BaseModel):
    """Request model for token update"""
    description: str = Field(..., description="New description for the token")
    
class MessageResponse(BaseModel):
    """Simple message response"""
    message: str
    
class AdminCreate(BaseModel):
    """Request model for admin creation"""
    username: str = Field(..., description="Admin username")
    password: str = Field(..., description="Admin password")
    
class AdminUpdate(BaseModel):
    """Request model for admin password update"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., description="New password")
    
class AdminResponse(BaseModel):
    """Response model for admin operations"""
    id: int
    username: str
    created_at: Optional[str] = None
    last_login: Optional[str] = None
    
class EfosUpdateResponse(BaseModel):
    """Response model for EFOS update operations"""
    status: str
    message: str
    details: Optional[Dict[str, Any]] = None

# Token management endpoints
@router.get("/tokens", response_model=Dict[str, Any])
async def get_tokens_endpoint(skip: int = 0, limit: int = 100):
    """
    Get all API tokens
    """
    try:
        tokens = await get_tokens(skip, limit)
        return {"tokens": tokens, "total": len(tokens)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting tokens: {str(e)}")

@router.post("/tokens", response_model=TokenResponse)
async def create_token_endpoint(token_data: TokenCreate):
    """
    Create a new API token
    """
    try:
        return await create_token(token_data.description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating token: {str(e)}")

@router.get("/tokens/{token_id}", response_model=TokenResponse)
async def get_token_endpoint(token_id: int = Path(..., description="Token ID")):
    """
    Get a specific API token by ID
    """
    try:
        token = await get_token_by_id(token_id)
        if not token:
            raise HTTPException(status_code=404, detail="Token not found")
        return token
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting token: {str(e)}")

@router.put("/tokens/{token_id}", response_model=TokenResponse)
async def update_token_endpoint(
    token_data: TokenUpdate,
    token_id: int = Path(..., description="Token ID")
):
    """
    Update an API token
    """
    try:
        token = await update_token(token_id, token_data.description)
        if not token:
            raise HTTPException(status_code=404, detail="Token not found")
        return token
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating token: {str(e)}")

@router.delete("/tokens/{token_id}", response_model=MessageResponse)
async def delete_token_endpoint(token_id: int = Path(..., description="Token ID")):
    """
    Delete an API token
    """
    try:
        result = await delete_token(token_id)
        if not result:
            raise HTTPException(status_code=404, detail="Token not found")
        return {"message": "Token deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting token: {str(e)}")

@router.post("/tokens/{token_id}/regenerate", response_model=TokenResponse)
async def regenerate_token_endpoint(token_id: int = Path(..., description="Token ID")):
    """
    Regenerate an API token (create a new token value)
    """
    try:
        token = await regenerate_token(token_id)
        if not token:
            raise HTTPException(status_code=404, detail="Token not found")
        return token
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error regenerating token: {str(e)}")

# Admin user management endpoints
@router.post("/superadmins", response_model=AdminResponse)
async def create_admin_endpoint(admin_data: AdminCreate):
    """
    Create a new admin user
    """
    try:
        return await create_admin(admin_data.username, admin_data.password)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating admin: {str(e)}")

@router.put("/superadmins/{username}/password", response_model=MessageResponse)
async def update_admin_password_endpoint(
    password_data: AdminUpdate,
    username: str = Path(..., description="Admin username")
):
    """
    Update an admin's password
    """
    try:
        result = await update_admin_password(
            username, 
            password_data.current_password, 
            password_data.new_password
        )
        if not result:
            raise HTTPException(status_code=404, detail="Admin not found or current password is incorrect")
        return {"message": "Password updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating admin password: {str(e)}")

@router.delete("/superadmins/{username}", response_model=MessageResponse)
async def deactivate_admin_endpoint(username: str = Path(..., description="Admin username")):
    """
    Deactivate an admin account
    """
    try:
        result = await deactivate_admin(username)
        if not result:
            raise HTTPException(status_code=404, detail="Admin not found")
        return {"message": "Admin deactivated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deactivating admin: {str(e)}")

# EFOS management endpoints
@router.get("/efos/metadata", response_model=Dict[str, Any])
async def get_efos_metadata_endpoint():
    """
    Get EFOS metadata information
    """
    try:
        metadata = await get_efos_metadata()
        if not metadata:
            raise HTTPException(status_code=404, detail="EFOS metadata not found")
        return metadata
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting EFOS metadata: {str(e)}")

@router.post("/efos/update", response_model=EfosUpdateResponse)
async def update_efos_database_endpoint(background_tasks: BackgroundTasks, run_in_background: bool = True):
    """
    Update the EFOS database by downloading the CSV from SAT
    
    The process can run in background or foreground.
    """
    try:
        if run_in_background:
            # Schedule update in background
            background_tasks.add_task(update_efos_database)
            return {
                "status": "processing",
                "message": "EFOS database update started in background",
                "details": None
            }
        else:
            # Run update in foreground
            result = await update_efos_database()
            
            status_msg = "success" if result.get("status") == "success" else "error"
            message = (
                f"EFOS database updated successfully. Imported {result.get('records_imported', 0)} records."
                if status_msg == "success"
                else f"Error updating EFOS database: {result.get('error_message', 'Unknown error')}"
            )
            
            return {
                "status": status_msg,
                "message": message,
                "details": result
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating EFOS database: {str(e)}") 