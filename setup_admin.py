import os
import getpass
from sqlalchemy.orm import Session
from database import get_db, create_tables
import admin_manager
import token_manager
from fastapi import HTTPException

def setup_initial_admin():
    """Set up the initial superadmin account and token"""
    print("=== CFDI API - Initial Setup ===")
    print("\nThis script will create the first superadmin account and an initial API token.")
    
    # Create tables if they don't exist
    create_tables()
    
    # Get DB session
    db = next(get_db())
    
    try:
        # Check if any superadmin exists
        username = input("\nEnter superadmin username: ")
        password = getpass.getpass("Enter superadmin password: ")
        confirm_password = getpass.getpass("Confirm password: ")
        
        if password != confirm_password:
            print("Passwords do not match. Please try again.")
            return
        
        # Create superadmin
        try:
            admin_manager.create_superadmin(db, username, password)
            print(f"\nSuperadmin '{username}' created successfully!")
        except HTTPException as e:
            if e.status_code == 400:
                print(f"\nWarning: {e.detail}. Please try again with a different username.")
                return
            raise
        
        # Create API token
        token_description = input("\nEnter a description for the API token (or leave empty): ")
        token = token_manager.create_token(db, token_description or "Initial API token")
        
        print("\n=== Setup Complete ===")
        print(f"Superadmin username: {username}")
        print(f"API Token: {token.token}")
        print("\nStore the API token securely! It won't be shown again.")
        
    except Exception as e:
        print(f"Error during setup: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    setup_initial_admin() 