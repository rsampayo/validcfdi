from sqlalchemy.orm import Session
from database import SuperAdmin
from security import get_password_hash, verify_password
from fastapi import HTTPException, status
from typing import Optional

# Create a new superadmin
def create_superadmin(db: Session, username: str, password: str) -> SuperAdmin:
    """
    Create a new superadmin in the database
    """
    # Check if superadmin already exists
    existing_admin = db.query(SuperAdmin).filter(SuperAdmin.username == username).first()
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Create new superadmin
    hashed_password = get_password_hash(password)
    db_admin = SuperAdmin(
        username=username,
        hashed_password=hashed_password,
        is_active=True
    )
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)
    return db_admin

# Get a superadmin by username
def get_superadmin_by_username(db: Session, username: str) -> Optional[SuperAdmin]:
    """
    Get a superadmin by username
    """
    return db.query(SuperAdmin).filter(SuperAdmin.username == username).first()

# Update superadmin password
def update_superadmin_password(db: Session, username: str, current_password: str, new_password: str) -> SuperAdmin:
    """
    Update a superadmin's password
    """
    # Get superadmin
    db_admin = get_superadmin_by_username(db, username)
    if not db_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Superadmin not found"
        )
    
    # Verify current password
    if not verify_password(current_password, db_admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    
    # Update password
    db_admin.hashed_password = get_password_hash(new_password)
    db.commit()
    db.refresh(db_admin)
    return db_admin

# Deactivate a superadmin
def deactivate_superadmin(db: Session, username: str) -> SuperAdmin:
    """
    Deactivate a superadmin account
    """
    db_admin = get_superadmin_by_username(db, username)
    if not db_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Superadmin not found"
        )
    
    db_admin.is_active = False
    db.commit()
    db.refresh(db_admin)
    return db_admin 