from sqlalchemy.orm import Session
from database import ApiToken
from security import generate_api_token
from fastapi import HTTPException, status
from datetime import datetime
from typing import List, Optional

# Create a new API token
def create_token(db: Session, description: Optional[str] = None) -> ApiToken:
    """
    Create a new API token in the database
    """
    new_token = generate_api_token()
    db_token = ApiToken(
        token=new_token,
        description=description,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token

# Get all API tokens
def get_all_tokens(db: Session, skip: int = 0, limit: int = 100) -> List[ApiToken]:
    """
    Get all API tokens from the database
    """
    return db.query(ApiToken).offset(skip).limit(limit).all()

# Get a specific API token by ID
def get_token_by_id(db: Session, token_id: int) -> Optional[ApiToken]:
    """
    Get a specific API token by its ID
    """
    return db.query(ApiToken).filter(ApiToken.id == token_id).first()

# Update an API token
def update_token(db: Session, token_id: int, description: Optional[str] = None, is_active: Optional[bool] = None) -> ApiToken:
    """
    Update an API token in the database
    """
    db_token = get_token_by_id(db, token_id)
    if not db_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    
    # Update fields if provided
    if description is not None:
        db_token.description = description
    if is_active is not None:
        db_token.is_active = is_active
    
    db_token.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_token)
    return db_token

# Delete an API token
def delete_token(db: Session, token_id: int) -> bool:
    """
    Delete an API token from the database
    """
    db_token = get_token_by_id(db, token_id)
    if not db_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    
    db.delete(db_token)
    db.commit()
    return True

# Regenerate an API token
def regenerate_token(db: Session, token_id: int) -> ApiToken:
    """
    Regenerate an API token with a new value
    """
    db_token = get_token_by_id(db, token_id)
    if not db_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    
    # Generate new token
    db_token.token = generate_api_token()
    db_token.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_token)
    return db_token 