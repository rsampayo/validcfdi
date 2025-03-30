#!/usr/bin/env python3
import schedule
import time
import threading
import logging
import os
import sys
import signal
import traceback
import requests
from datetime import datetime, timedelta
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
# Default to 24 hours (1 day)
UPDATE_INTERVAL_DAYS = int(os.environ.get("EFOS_UPDATE_INTERVAL_DAYS", "1"))
UPDATE_TIME = os.environ.get("EFOS_UPDATE_TIME", "03:00")  # Default is 3 AM
HEALTHCHECK_URL = os.environ.get("EFOS_HEALTHCHECK_URL")
HEALTHCHECK_INTERVAL_MINUTES = int(os.environ.get("EFOS_HEALTHCHECK_INTERVAL_MINUTES", "60"))
MAX_MEMORY_PERCENT = int(os.environ.get("EFOS_MAX_MEMORY_PERCENT", "90"))
KEEP_ALIVE_URL = os.environ.get("KEEP_ALIVE_URL")  # URL to ping to keep dyno alive

# Global state for heartbeat
last_successful_run = None
is_job_running = False
worker_started_at = datetime.now()
heartbeat_counter = 0

def get_db_session():
    """Get a database session"""
    try:
        return SessionLocal()
    except Exception as e:
        logger.error(f"Error creating database session: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def send_heartbeat(success=True, error_message=None):
    """
    Send a heartbeat to a monitoring service if configured
    """
    global heartbeat_counter
    
    if not HEALTHCHECK_URL:
        return
        
    try:
        heartbeat_counter += 1
        
        memory_usage = get_memory_usage()
        uptime_seconds = (datetime.now() - worker_started_at).total_seconds()
        
        data = {
            "status": "success" if success else "error",
            "timestamp": datetime.now().isoformat(),
            "message": error_message if error_message else "Heartbeat check",
            "uptime_seconds": int(uptime_seconds),
            "last_successful_run": last_successful_run.isoformat() if last_successful_run else None,
            "memory_usage_percent": memory_usage,
            "counter": heartbeat_counter
        }
        
        requests.post(HEALTHCHECK_URL, json=data, timeout=10)
        logger.debug(f"Sent heartbeat to {HEALTHCHECK_URL}")
    except Exception as e:
        logger.warning(f"Failed to send heartbeat: {str(e)}")

def get_memory_usage():
    """
    Get memory usage percentage for the current process
    """
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_percent()
    except ImportError:
        logger.debug("psutil not installed, cannot check memory usage")
        return None
    except Exception as e:
        logger.warning(f"Error checking memory usage: {str(e)}")
        return None

def keep_alive():
    """
    Ping an application URL to keep the Heroku dyno alive
    """
    if not KEEP_ALIVE_URL:
        return
        
    try:
        response = requests.get(KEEP_ALIVE_URL, timeout=10)
        logger.debug(f"Keep-alive ping sent to {KEEP_ALIVE_URL}, status: {response.status_code}")
    except Exception as e:
        logger.warning(f"Failed to send keep-alive ping: {str(e)}")

def check_memory_usage():
    """
    Check memory usage and log a warning if it's too high
    """
    memory_usage = get_memory_usage()
    
    if memory_usage and memory_usage > MAX_MEMORY_PERCENT:
        logger.warning(f"⚠️ High memory usage: {memory_usage:.1f}% (limit: {MAX_MEMORY_PERCENT}%)")
        # Could consider forcing garbage collection here or restarting
        import gc
        logger.info("Forcing garbage collection")
        gc.collect()

def update_efos_database_job():
    """Job to update the EFOS database"""
    global is_job_running, last_successful_run
    
    # Prevent concurrent runs
    if is_job_running:
        logger.warning("Update job already running, skipping this execution")
        return
        
    is_job_running = True
    job_start_time = datetime.now()
    start_msg = f"EFOS database check job started at {job_start_time.isoformat()}"
    logger.info(start_msg)
    print(start_msg)
    
    try:
        # Create database session
        db = get_db_session()
        if not db:
            error_msg = "Failed to create database session, aborting job"
            logger.error(error_msg)
            print(error_msg)
            send_heartbeat(success=False, error_message=error_msg)
            is_job_running = False
            return
        
        try:
            # Check memory before running update
            check_memory_usage()
            
            # Run update
            result = efos_manager.update_efos_database(db)
            
            # Log result based on status
            if result.get("status") == "success":
                last_successful_run = datetime.now()
                msg = f"✅ EFOS database update COMPLETED SUCCESSFULLY - File has changed"
                logger.info(msg)
                print(msg)
                details = f"Processed {result.get('records_processed', 0)} records, imported {result.get('records_imported', 0)} records in {result.get('processing_time_seconds', 0):.2f} seconds."
                logger.info(details)
                print(details)
                send_heartbeat(success=True)
            elif result.get("status") == "unchanged":
                last_successful_run = datetime.now()  # Count as successful even though no changes
                msg = f"ℹ️ EFOS database update SKIPPED - File has not changed since last update"
                logger.info(msg)
                print(msg)
                details = f"Check completed in {result.get('processing_time_seconds', 0):.2f} seconds."
                logger.info(details)
                print(details)
                send_heartbeat(success=True)
            else:
                msg = f"❌ EFOS database update FAILED: {result.get('error_message', 'Unknown error')}"
                logger.error(msg)
                print(msg)
                send_heartbeat(success=False, error_message=result.get('error_message'))
        except Exception as e:
            error_msg = f"Error in EFOS database update job: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            print(error_msg)
            send_heartbeat(success=False, error_message=str(e))
        finally:
            # Close database session
            if db:
                db.close()
    except Exception as e:
        error_msg = f"Unhandled error in update job: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        print(error_msg)
        send_heartbeat(success=False, error_message=str(e))
    finally:
        is_job_running = False
        
        # Run garbage collection to free memory
        try:
            import gc
            gc.collect()
        except:
            pass
        
        # Check memory after running update
        check_memory_usage()
        
        job_end_time = datetime.now()
        job_duration = (job_end_time - job_start_time).total_seconds()
        end_msg = f"EFOS database check job finished at {job_end_time.isoformat()} (took {job_duration:.2f} seconds)"
        logger.info(end_msg)
        print(end_msg)

def run_threaded(job_func):
    """Run a job in a separate thread"""
    job_thread = threading.Thread(target=job_func)
    job_thread.daemon = True  # Set as daemon so it exits when main thread exits
    job_thread.start()

def heartbeat_job():
    """Job to send periodic heartbeats"""
    try:
        global last_successful_run
        
        # Calculate time since last successful run
        time_since_last_run = None
        if last_successful_run:
            time_since_last_run = (datetime.now() - last_successful_run).total_seconds() / 3600  # hours
            
        if time_since_last_run is not None:
            next_run = get_next_scheduled_run()
            hours_until_next_run = (next_run - datetime.now()).total_seconds() / 3600 if next_run else None
            
            logger.info(f"Heartbeat: {time_since_last_run:.1f} hours since last successful run, {hours_until_next_run:.1f} hours until next run")
        
        send_heartbeat()
        
        # Also send a keep-alive request
        keep_alive()
        
    except Exception as e:
        logger.error(f"Error in heartbeat job: {str(e)}")

def get_next_scheduled_run():
    """Get the datetime of the next scheduled run"""
    try:
        for job in schedule.jobs:
            if job.job_func.args and job.job_func.args[0].__name__ == 'update_efos_database_job':
                return job.next_run
        return None
    except Exception as e:
        logger.error(f"Error getting next scheduled run: {str(e)}")
        return None

def setup_schedule():
    """Setup the job schedule"""
    logger.info(f"Setting up EFOS database update schedule: every {UPDATE_INTERVAL_DAYS} day(s) at {UPDATE_TIME}")
    
    # Schedule the update job
    if UPDATE_INTERVAL_DAYS == 1:
        schedule.every().day.at(UPDATE_TIME).do(run_threaded, update_efos_database_job)
    else:
        schedule.every(UPDATE_INTERVAL_DAYS).days.at(UPDATE_TIME).do(run_threaded, update_efos_database_job)
    
    # Setup heartbeat job
    if HEALTHCHECK_URL:
        logger.info(f"Setting up heartbeat job every {HEALTHCHECK_INTERVAL_MINUTES} minutes")
        schedule.every(HEALTHCHECK_INTERVAL_MINUTES).minutes.do(run_threaded, heartbeat_job)
    
    # Setup keep-alive job (every 25 minutes to avoid Heroku's 30-minute timeout)
    if KEEP_ALIVE_URL:
        logger.info(f"Setting up keep-alive job every 25 minutes")
        schedule.every(25).minutes.do(run_threaded, keep_alive)
    
    logger.info("Schedule setup complete")

def handle_sigterm(signum, frame):
    """
    Handle SIGTERM signal (sent by Heroku when shutting down dynos)
    """
    logger.info("Received SIGTERM, shutting down gracefully...")
    
    # Send final heartbeat
    send_heartbeat(success=True, error_message="Received shutdown signal")
    
    # Exit with status 0 to indicate successful shutdown
    sys.exit(0)

def run_scheduler():
    """Main function to run the scheduler"""
    signal.signal(signal.SIGTERM, handle_sigterm)
    
    header = "========================================="
    logger.info(header)
    print(header)
    
    start_msg = "Starting EFOS scheduler"
    logger.info(start_msg)
    print(start_msg)
    
    config_msg = f"Will check for updates every {UPDATE_INTERVAL_DAYS} day(s) at {UPDATE_TIME}"
    logger.info(config_msg)
    print(config_msg)
    
    logger.info(header)
    print(header)
    
    # Send initial heartbeat
    send_heartbeat(success=True, error_message="Worker started")
    
    # Setup the job schedule
    setup_schedule()
    
    # Run the initial job immediately
    init_msg = "Running initial EFOS database update"
    logger.info(init_msg)
    print(init_msg)
    run_threaded(update_efos_database_job)
    
    # Run the scheduler loop with error handling
    loop_msg = "Running scheduler loop"
    logger.info(loop_msg)
    print(loop_msg)
    
    last_error_time = None
    consecutive_errors = 0
    
    try:
        while True:
            try:
                # Check for pending jobs
                schedule.run_pending()
                
                # Sleep for a bit to avoid high CPU usage
                time.sleep(10)
                
                # Reset error counter if no errors
                if consecutive_errors > 0:
                    consecutive_errors = 0
                    
            except Exception as e:
                # Handle errors in the scheduler loop
                error_time = datetime.now()
                consecutive_errors += 1
                
                # Only log detailed error if it's new or happened more than 10 minutes ago
                if not last_error_time or (error_time - last_error_time).total_seconds() > 600:
                    error_msg = f"Scheduler loop error: {str(e)}"
                    logger.error(error_msg)
                    logger.error(traceback.format_exc())
                    print(error_msg)
                    last_error_time = error_time
                
                # Send heartbeat for serious errors or after multiple consecutive errors
                if consecutive_errors >= 5:
                    send_heartbeat(success=False, error_message=f"Multiple scheduler errors: {str(e)}")
                    
                    # If we've had too many errors in a row, restart the scheduler
                    if consecutive_errors >= 10:
                        logger.critical("Too many consecutive errors, attempting restart")
                        
                        # Force scheduler to reset
                        schedule.clear()
                        setup_schedule()
                        consecutive_errors = 0
                
                # Sleep a bit longer after an error
                time.sleep(30)
                
    except KeyboardInterrupt:
        stop_msg = "Scheduler stopped by user"
        logger.info(stop_msg)
        print(stop_msg)
        send_heartbeat(success=True, error_message="Stopped by user")
    except Exception as e:
        error_msg = f"Fatal scheduler error: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        print(error_msg)
        send_heartbeat(success=False, error_message=f"Fatal error: {str(e)}")
    
    end_msg = "EFOS scheduler stopped"
    logger.info(end_msg)
    print(end_msg)

if __name__ == "__main__":
    # Create database tables if they don't exist
    try:
        create_tables()
    except Exception as e:
        logger.critical(f"Failed to create database tables: {str(e)}")
        logger.critical(traceback.format_exc())
        sys.exit(1)
    
    # Check if psutil is available for memory monitoring
    try:
        import psutil
        logger.info("psutil is available for memory monitoring")
    except ImportError:
        logger.warning("psutil is not installed, memory monitoring will be disabled")
        logger.warning("Consider installing it with: pip install psutil")
    
    # Run the scheduler
    run_scheduler() 