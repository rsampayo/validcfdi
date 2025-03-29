from database import get_db, create_tables
import token_manager

def main():
    # Create tables if they don't exist
    create_tables()
    
    # Get DB session
    db = next(get_db())
    
    try:
        # List all existing tokens
        existing_tokens = token_manager.get_all_tokens(db)
        
        print("Existing tokens:")
        if existing_tokens:
            for token in existing_tokens:
                print(f"ID: {token.id}, Token: {token.token}, Description: {token.description}, Active: {token.is_active}")
        else:
            print("No tokens found.")
        
        # Create a new token for testing if needed
        create_new = input("\nCreate a new token? (y/n): ")
        if create_new.lower() == 'y':
            description = input("Enter token description: ")
            new_token = token_manager.create_token(db, description)
            print(f"\nNew token created:")
            print(f"ID: {new_token.id}, Token: {new_token.token}, Description: {new_token.description}")
    
    finally:
        db.close()

if __name__ == "__main__":
    main() 