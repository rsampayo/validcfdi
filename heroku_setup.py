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
from database import create_tables, get_db
from admin_manager import create_superadmin, get_superadmin_by_username
from token_manager import create_token, get_all_tokens
from efos_manager import get_efos_metadata
from schemas import SuperAdminCreate, TokenCreate
from migrations import run_migrations

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("heroku_setup")

def setup_database():
    """Set up the database tables"""
    start_time = time.time()
    logger.info("Running Database setup...")
    
    try:
        # Run migrations first
        logger.info("Running database migrations...")
        if not run_migrations():
            logger.error("❌ Database migrations failed")
            return False
        logger.info("✅ Database migrations completed")
        
        # Create tables
        logger.info("Creating database tables...")
        create_tables()
        duration = time.time() - start_time
        logger.info(f"✅ Database setup successful")
        logger.info(f"✅ Database setup completed in {duration:.2f} seconds")
        return True
    except Exception as e:
        logger.error(f"❌ Database setup failed: {str(e)}")
        logger.error(f"❌ Database setup failed after {time.time() - start_time:.2f} seconds")
        return False

def setup_admin():
    """Set up the initial admin user"""
    start_time = time.time()
    logger.info("Running Admin setup...")
    
    try:
        # Get admin credentials from environment
        username = os.environ.get("SUPERADMIN_USERNAME")
        password = os.environ.get("SUPERADMIN_PASSWORD")
        
        if not username or not password:
            logger.warning("⚠️ No admin credentials provided, skipping admin setup")
            return True
        
        logger.info("Setting up initial admin user...")
        db = next(get_db())
        try:
            # Check if admin exists
            admin = get_superadmin_by_username(db, username)
            if not admin:
                # Create admin if doesn't exist
                admin = create_superadmin(db, SuperAdminCreate(
                    username=username,
                    password=password
                ))
                logger.info(f"✅ Created admin user: {username}")
            else:
                logger.info(f"✅ Admin user already exists: {username}")
            
            duration = time.time() - start_time
            logger.info(f"✅ Admin setup completed in {duration:.2f} seconds")
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Admin setup failed: {str(e)}")
        logger.error(f"❌ Admin setup failed after {time.time() - start_time:.2f} seconds")
        return False

def setup_api_token():
    """Set up the default API token"""
    start_time = time.time()
    logger.info("Running API token setup...")
    
    try:
        # Get token from environment
        token = os.environ.get("DEFAULT_API_TOKEN")
        
        if not token:
            logger.warning("⚠️ No default API token provided, skipping token setup")
            return True
        
        logger.info("Setting up default API token...")
        db = next(get_db())
        try:
            # Check if any tokens exist
            tokens = get_all_tokens(db)
            if not tokens:
                # Create default token if no tokens exist
                create_token(db, TokenCreate(
                    description="Default API Token",
                    token=token
                ))
                logger.info("✅ Created default API token")
            else:
                logger.info("✅ API tokens already exist")
            
            duration = time.time() - start_time
            logger.info(f"✅ API token setup completed in {duration:.2f} seconds")
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ API token setup failed: {str(e)}")
        logger.error(f"❌ API token setup failed after {time.time() - start_time:.2f} seconds")
        return False

def schedule_efos_download():
    """Schedule the initial EFOS data download"""
    start_time = time.time()
    logger.info("Running EFOS download setup...")
    
    try:
        logger.info("Scheduling initial EFOS data download...")
        db = next(get_db())
        try:
            # Check if EFOS metadata exists
            metadata = get_efos_metadata(db)
            if not metadata:
                logger.info("✅ No EFOS metadata found, worker will handle initial download")
            else:
                logger.info("✅ EFOS metadata exists, worker will handle updates")
            
            duration = time.time() - start_time
            logger.info(f"✅ EFOS download setup completed in {duration:.2f} seconds")
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ EFOS download setup failed: {str(e)}")
        logger.error(f"❌ EFOS download setup failed after {time.time() - start_time:.2f} seconds")
        return False

def main():
    """Main setup function"""
    start_time = time.time()
    logger.info("===================================")
    logger.info("Starting Heroku setup")
    logger.info(f"Environment: {os.environ.get('ENVIRONMENT', 'production')}")
    logger.info(f"Database URL: {os.environ.get('DATABASE_URL', '').split('@')[1] if '@' in os.environ.get('DATABASE_URL', '') else '...'}")
    logger.info("===================================")
    
    # Run all setup steps
    success = all([
        setup_database(),
        setup_admin(),
        setup_api_token(),
        schedule_efos_download()
    ])
    
    duration = time.time() - start_time
    if success:
        logger.info(f"✅ Heroku setup completed successfully in {duration:.2f} seconds")
    else:
        logger.error(f"❌ Heroku setup completed with errors in {duration:.2f} seconds")

if __name__ == "__main__":
    main() 