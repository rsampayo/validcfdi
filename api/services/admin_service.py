"""
Admin Service

Functions for managing admin users.
"""
from typing import Dict, Any, Optional, List
import logging
import datetime
import hashlib
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Example admin data (this would come from a database in a real implementation)
ADMINS = [
    {
        "id": 1,
        "username": os.getenv("SUPERADMIN_USERNAME", "admin"),
        "password_hash": hashlib.sha256(
            os.getenv("SUPERADMIN_PASSWORD", "caragram").encode()
        ).hexdigest(),
        "created_at": "2025-01-01T00:00:00.000000",
        "last_login": "2025-03-30T12:34:56.789012",
        "is_active": True
    }
]

# Admin ID counter
ADMIN_ID_COUNTER = 2

def hash_password(password: str) -> str:
    """
    Hash a password using SHA-256
    
    Args:
        password: Password to hash
        
    Returns:
        Hashed password
    """
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hash: str) -> bool:
    """
    Verify a password against a hash
    
    Args:
        password: Password to verify
        hash: Hash to verify against
        
    Returns:
        True if the password matches the hash, False otherwise
    """
    return hash_password(password) == hash

async def get_admin_by_username(username: str) -> Optional[Dict[str, Any]]:
    """
    Get an admin by username
    
    Args:
        username: Username to search for
        
    Returns:
        Admin dictionary or None if not found
    """
    logger.info(f"Getting admin by username: {username}")
    
    # In a real implementation, this would query a database
    # For now, we'll just search our example admins
    for admin in ADMINS:
        if admin["username"] == username and admin["is_active"]:
            return admin
    
    return None

async def create_admin(username: str, password: str) -> Dict[str, Any]:
    """
    Create a new admin user
    
    Args:
        username: Username for the new admin
        password: Password for the new admin
        
    Returns:
        New admin dictionary
    """
    global ADMIN_ID_COUNTER
    
    logger.info(f"Creating new admin: {username}")
    
    # Check if username already exists
    existing_admin = await get_admin_by_username(username)
    if existing_admin:
        raise ValueError(f"Admin with username '{username}' already exists")
    
    # Create the admin
    new_admin = {
        "id": ADMIN_ID_COUNTER,
        "username": username,
        "password_hash": hash_password(password),
        "created_at": datetime.datetime.now().isoformat(),
        "last_login": None,
        "is_active": True
    }
    
    # Increment the counter
    ADMIN_ID_COUNTER += 1
    
    # Add to the list (in a real implementation, this would be saved to a database)
    ADMINS.append(new_admin)
    
    logger.info(f"Created new admin with ID {new_admin['id']}")
    
    # Return a copy without the password hash
    admin_copy = new_admin.copy()
    del admin_copy["password_hash"]
    return admin_copy

async def update_admin_password(username: str, current_password: str, new_password: str) -> bool:
    """
    Update an admin's password
    
    Args:
        username: Username of the admin
        current_password: Current password (for verification)
        new_password: New password
        
    Returns:
        True if the password was updated, False otherwise
    """
    logger.info(f"Updating password for admin: {username}")
    
    # Find the admin
    admin = await get_admin_by_username(username)
    if not admin:
        logger.warning(f"Admin '{username}' not found")
        return False
    
    # Verify current password
    if not verify_password(current_password, admin["password_hash"]):
        logger.warning(f"Current password verification failed for admin: {username}")
        return False
    
    # Update the password
    admin["password_hash"] = hash_password(new_password)
    
    logger.info(f"Updated password for admin: {username}")
    
    return True

async def deactivate_admin(username: str) -> bool:
    """
    Deactivate an admin account
    
    Args:
        username: Username of the admin to deactivate
        
    Returns:
        True if the admin was deactivated, False if not found
    """
    logger.info(f"Deactivating admin: {username}")
    
    # Find the admin
    admin = await get_admin_by_username(username)
    if not admin:
        logger.warning(f"Admin '{username}' not found")
        return False
    
    # Deactivate the admin
    admin["is_active"] = False
    
    logger.info(f"Deactivated admin: {username}")
    
    return True 