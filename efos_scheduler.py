#!/usr/bin/env python3
import schedule
import time
import threading
import logging
import os
from datetime import datetime
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import database and EFOS manager
from database import create_tables, SessionLocal
import efos_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("efos_scheduler.log")
    ]
)
logger = logging.getLogger("efos_scheduler")

# Configuration
UPDATE_INTERVAL_DAYS = int(os.environ.get("EFOS_UPDATE_INTERVAL_DAYS", "1"))
UPDATE_TIME = os.environ.get("EFOS_UPDATE_TIME", "03:00")  # Default is 3 AM

def get_db_session():
    """Get a database session"""
    return SessionLocal()

def update_efos_database_job():
    """Job to update the EFOS database"""
    logger.info(f"EFOS database update job started at {datetime.now().isoformat()}")
    
    try:
        # Create database session
        db = get_db_session()
        
        # Run update
        result = efos_manager.update_efos_database(db)
        
        # Log result
        if result.get("status") == "success":
            logger.info(f"EFOS database update completed successfully. Processed {result.get('records_processed', 0)} records, imported {result.get('records_imported', 0)} records in {result.get('processing_time_seconds', 0):.2f} seconds.")
        else:
            logger.error(f"EFOS database update failed: {result.get('error_message', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Error in EFOS database update job: {str(e)}")
    finally:
        # Close database session
        db.close()
        
    logger.info(f"EFOS database update job finished at {datetime.now().isoformat()}")

def run_threaded(job_func):
    """Run a job in a separate thread"""
    job_thread = threading.Thread(target=job_func)
    job_thread.start()

def setup_schedule():
    """Setup the job schedule"""
    logger.info(f"Setting up EFOS database update schedule: every {UPDATE_INTERVAL_DAYS} day(s) at {UPDATE_TIME}")
    
    # Schedule the update job
    if UPDATE_INTERVAL_DAYS == 1:
        schedule.every().day.at(UPDATE_TIME).do(run_threaded, update_efos_database_job)
    else:
        schedule.every(UPDATE_INTERVAL_DAYS).days.at(UPDATE_TIME).do(run_threaded, update_efos_database_job)
    
    logger.info("Schedule setup complete")

def run_scheduler():
    """Main function to run the scheduler"""
    logger.info("Starting EFOS scheduler")
    
    # Setup the job schedule
    setup_schedule()
    
    # Run the initial job immediately
    logger.info("Running initial EFOS database update")
    run_threaded(update_efos_database_job)
    
    # Run the scheduler loop
    logger.info("Running scheduler loop")
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check for pending jobs every minute
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {str(e)}")
    
    logger.info("EFOS scheduler stopped")

if __name__ == "__main__":
    # Create database tables if they don't exist
    create_tables()
    
    # Run the scheduler
    run_scheduler() 