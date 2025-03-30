from sqlalchemy import create_engine, text
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations():
    # Get database URL from environment
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL not set")
        return False
    
    # Convert Heroku's postgres:// to postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        # Add last_login column to superadmins table if it doesn't exist
        with engine.connect() as conn:
            # Check if last_login column exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'superadmins' 
                AND column_name = 'last_login';
            """))
            
            if not result.fetchone():
                logger.info("Adding last_login column to superadmins table...")
                conn.execute(text("""
                    ALTER TABLE superadmins 
                    ADD COLUMN last_login TIMESTAMP;
                """))
                conn.commit()
                logger.info("✅ Added last_login column to superadmins table")
            else:
                logger.info("last_login column already exists in superadmins table")
            
            # Check if error_message column exists in efos_metadata
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'efos_metadata' 
                AND column_name = 'error_message';
            """))
            
            if not result.fetchone():
                logger.info("Adding error_message column to efos_metadata table...")
                conn.execute(text("""
                    ALTER TABLE efos_metadata 
                    ADD COLUMN error_message TEXT;
                """))
                conn.commit()
                logger.info("✅ Added error_message column to efos_metadata table")
            else:
                logger.info("error_message column already exists in efos_metadata table")
        
        logger.info("✅ All migrations completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    run_migrations() 