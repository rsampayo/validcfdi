#!/usr/bin/env python3
"""
Heroku setup script - runs during release phase

This script:
1. Creates database tables
2. Sets up the initial admin user
3. Schedules initial EFOS data download
"""

import os
import sys
import logging
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("heroku_setup")

def setup_database():
    """Create database tables"""
    try:
        logger.info("Creating database tables...")
        from database import create_tables, SessionLocal
        
        # Create tables
        create_tables()
        
        # Test database connection
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        
        logger.info("✅ Database setup successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database setup failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def setup_admin():
    """Set up initial admin user"""
    try:
        logger.info("Setting up initial admin user...")
        
        # Check if admin credentials are configured
        username = os.environ.get("SUPERADMIN_USERNAME")
        password = os.environ.get("SUPERADMIN_PASSWORD")
        
        if not username or not password:
            logger.warning("⚠️ SUPERADMIN_USERNAME or SUPERADMIN_PASSWORD not set, skipping admin setup")
            return True
            
        # Import admin manager
        import admin_manager
        from database import SessionLocal
        from schemas import SuperAdminCreate
        
        # Create admin user
        db = SessionLocal()
        try:
            admin = admin_manager.get_superadmin_by_username(db, username)
            if not admin:
                admin_manager.create_superadmin(db, SuperAdminCreate(
                    username=username,
                    password=password
                ))
                logger.info(f"✅ Created superadmin user: {username}")
            else:
                logger.info(f"✅ Superadmin user {username} already exists")
        finally:
            db.close()
            
        return True
    except Exception as e:
        logger.error(f"❌ Admin setup failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def setup_api_token():
    """Set up default API token"""
    try:
        logger.info("Setting up default API token...")
        
        # Check if token is configured
        default_token = os.environ.get("DEFAULT_API_TOKEN")
        
        if not default_token:
            logger.warning("⚠️ DEFAULT_API_TOKEN not set, skipping token setup")
            return True
            
        # Import token manager
        import token_manager
        from database import SessionLocal
        from schemas import TokenCreate
        
        # Create token
        db = SessionLocal()
        try:
            tokens = token_manager.get_all_tokens(db)
            if not tokens:
                token_manager.create_token(db, TokenCreate(
                    description="Default API Token",
                    token=default_token
                ))
                logger.info("✅ Created default API token")
            else:
                logger.info("✅ API tokens already exist")
        finally:
            db.close()
            
        return True
    except Exception as e:
        logger.error(f"❌ API token setup failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def schedule_efos_download():
    """Queue initial EFOS data download"""
    try:
        logger.info("Scheduling initial EFOS data download...")
        
        # Import required modules
        from database import SessionLocal
        import efos_manager
        
        # Check if EFOS records already exist
        db = SessionLocal()
        try:
            # Check if we already have EFOS metadata
            from database import EfosMetadata
            metadata = db.query(EfosMetadata).first()
            
            if metadata:
                logger.info("✅ EFOS metadata already exists, skipping initial download")
                logger.info(f"   Last updated: {metadata.last_updated}")
                logger.info(f"   Last checked: {metadata.last_checked}")
                return True
                
            # No metadata exists, schedule initial download
            # We don't want to block the Heroku startup, so we'll just ensure tables exist
            # and let the worker handle the download
            logger.info("✅ EFOS tables ready for worker to download data")
            
        finally:
            db.close()
            
        return True
    except Exception as e:
        logger.error(f"❌ EFOS setup failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Run all setup steps"""
    logger.info("===================================")
    logger.info("Starting Heroku setup")
    logger.info(f"Environment: {os.environ.get('ENVIRONMENT', 'production')}")
    logger.info(f"Database URL: {os.environ.get('DATABASE_URL', 'Not set')[:20]}...")
    logger.info("===================================")
    
    start_time = time.time()
    
    # Run setup steps
    steps = [
        ("Database setup", setup_database),
        ("Admin setup", setup_admin),
        ("API token setup", setup_api_token),
        ("EFOS download setup", schedule_efos_download)
    ]
    
    success = True
    
    for name, func in steps:
        step_start = time.time()
        logger.info(f"Running {name}...")
        
        step_success = func()
        step_time = time.time() - step_start
        
        if step_success:
            logger.info(f"✅ {name} completed in {step_time:.2f} seconds")
        else:
            logger.error(f"❌ {name} failed after {step_time:.2f} seconds")
            success = False
    
    # Log completion
    total_time = time.time() - start_time
    if success:
        logger.info(f"✅ Heroku setup completed successfully in {total_time:.2f} seconds")
    else:
        logger.error(f"❌ Heroku setup completed with errors in {total_time:.2f} seconds")
        sys.exit(1)

if __name__ == "__main__":
    main() 