from database import get_db, create_tables
import admin_manager
import token_manager
from fastapi import HTTPException

def create_initial_admin():
    """Create initial superadmin and token with hardcoded values (for testing)"""
    username = "admin"
    password = "password"
    
    print(f"Creating superadmin: {username}")
    
    # Create tables
    create_tables()
    
    # Get DB session
    db = next(get_db())
    
    try:
        # Create superadmin
        try:
            admin = admin_manager.create_superadmin(db, username, password)
            print(f"Superadmin created: {admin.username}")
        except HTTPException as e:
            if e.status_code == 400:
                print(f"Superadmin already exists: {e.detail}")
            else:
                raise
        
        # Create API token
        token = token_manager.create_token(db, "Default API token")
        print(f"API token created: {token.token}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_initial_admin() 