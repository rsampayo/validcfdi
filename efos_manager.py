import os
import requests
import io
import csv
import tempfile
import subprocess
import hashlib
from datetime import datetime
import time
import sys
import traceback
from sqlalchemy.orm import Session
from sqlalchemy import delete, select, func
from typing import List, Dict, Optional, Tuple, Generator
import logging
from pathlib import Path

from database import EfosRecord, EfosMetadata

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# URL of the EFOS CSV file from SAT
EFOS_CSV_URL = os.environ.get("EFOS_CSV_URL", "http://omawww.sat.gob.mx/cifras_sat/Documents/Listado_Completo_69-B.csv")

# Configuration for retry logic
MAX_RETRIES = int(os.environ.get("EFOS_MAX_RETRIES", "3"))
RETRY_BACKOFF = int(os.environ.get("EFOS_RETRY_BACKOFF_SECONDS", "5"))

# Configuration for chunked operations
DOWNLOAD_CHUNK_SIZE = int(os.environ.get("EFOS_DOWNLOAD_CHUNK_SIZE", "8192"))  # 8KB chunks
IMPORT_BATCH_SIZE = int(os.environ.get("EFOS_IMPORT_BATCH_SIZE", "1000"))  # Records per transaction

# Configuration for database size monitoring
MAX_DB_SIZE_MB = int(os.environ.get("EFOS_MAX_DB_SIZE_MB", "500"))  # 500MB default max size

def get_file_metadata(url: str = None) -> Dict:
    """
    Gets metadata about the remote file using HEAD request with retry logic
    
    Args:
        url: URL of the file (defaults to EFOS_CSV_URL)
        
    Returns:
        Dictionary with file metadata
    """
    if url is None:
        url = EFOS_CSV_URL
        
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            logger.info(f"Checking metadata for file at {url} (attempt {retry_count+1}/{MAX_RETRIES})")
            response = requests.head(url, timeout=30)
            response.raise_for_status()
            
            # Get HTTP headers
            headers = response.headers
            
            metadata = {
                "etag": headers.get("ETag"),
                "last_modified": headers.get("Last-Modified"),
                "content_length": headers.get("Content-Length"),
                "content_type": headers.get("Content-Type"),
                "checked_at": datetime.utcnow().isoformat()
            }
            
            size_mb = int(metadata.get("content_length", "0")) / 1024 / 1024 if metadata.get("content_length") else "unknown"
            logger.info(f"File metadata: ETag: {metadata['etag']}, Last-Modified: {metadata['last_modified']}, Size: {size_mb:.2f}MB")
            return metadata
            
        except requests.RequestException as e:
            retry_count += 1
            if retry_count < MAX_RETRIES:
                wait_time = RETRY_BACKOFF * retry_count
                logger.warning(f"Error getting file metadata (attempt {retry_count}/{MAX_RETRIES}): {str(e)}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"Error getting file metadata after {MAX_RETRIES} attempts: {str(e)}")
                raise Exception(f"Failed to get file metadata after {MAX_RETRIES} attempts: {str(e)}")

def calculate_file_hash(content: bytes) -> str:
    """
    Calculates a SHA-256 hash of the file content
    
    Args:
        content: File content in bytes
        
    Returns:
        Hash as a hex string
    """
    return hashlib.sha256(content).hexdigest()

def has_file_changed(db: Session, content: bytes = None) -> Tuple[bool, Dict]:
    """
    Checks if the EFOS file has changed since the last update
    
    Args:
        db: Database session
        content: Optional file content in bytes (if already downloaded)
        
    Returns:
        Tuple with (has_changed, metadata)
    """
    try:
        # Get current metadata from remote file
        remote_metadata = get_file_metadata()
        
        # Get last saved metadata from database
        metadata_record = db.query(EfosMetadata).first()
        
        if metadata_record is None:
            logger.info("No previous metadata found, file considered changed")
            
            # If content is provided, calculate its hash
            if content:
                remote_metadata["content_hash"] = calculate_file_hash(content)
                
            return True, remote_metadata
        
        # Check if ETag or Last-Modified have changed
        if remote_metadata.get("etag") and metadata_record.etag:
            if remote_metadata["etag"] != metadata_record.etag:
                logger.info(f"ETag has changed: {metadata_record.etag} -> {remote_metadata['etag']}")
                
                # Calculate hash if content is available
                if content:
                    remote_metadata["content_hash"] = calculate_file_hash(content)
                    
                return True, remote_metadata
        
        if remote_metadata.get("last_modified") and metadata_record.last_modified:
            if remote_metadata["last_modified"] != metadata_record.last_modified:
                logger.info(f"Last-Modified has changed: {metadata_record.last_modified} -> {remote_metadata['last_modified']}")
                
                # Calculate hash if content is available
                if content:
                    remote_metadata["content_hash"] = calculate_file_hash(content)
                    
                return True, remote_metadata
        
        # If we have content, we can do a hash comparison regardless of headers
        if content:
            content_hash = calculate_file_hash(content)
            remote_metadata["content_hash"] = content_hash
            
            if not metadata_record.content_hash or content_hash != metadata_record.content_hash:
                logger.info(f"Content hash has changed: {metadata_record.content_hash} -> {content_hash}")
                return True, remote_metadata
                
        # No changes detected
        logger.info("No changes detected in EFOS file")
        return False, remote_metadata
        
    except Exception as e:
        logger.error(f"Error checking if file has changed: {str(e)}")
        # If we can't determine if the file has changed, assume it has as a precaution
        return True, {}

def save_metadata(db: Session, metadata: Dict) -> None:
    """
    Saves file metadata to the database
    
    Args:
        db: Database session
        metadata: Dictionary with metadata to save
    """
    try:
        # Get existing metadata or create new
        metadata_record = db.query(EfosMetadata).first()
        
        if metadata_record is None:
            metadata_record = EfosMetadata(
                etag=metadata.get("etag"),
                last_modified=metadata.get("last_modified"),
                content_length=metadata.get("content_length"),
                content_type=metadata.get("content_type"),
                content_hash=metadata.get("content_hash"),
                last_updated=datetime.utcnow(),
                last_checked=datetime.utcnow()
            )
            db.add(metadata_record)
        else:
            metadata_record.etag = metadata.get("etag", metadata_record.etag)
            metadata_record.last_modified = metadata.get("last_modified", metadata_record.last_modified)
            metadata_record.content_length = metadata.get("content_length", metadata_record.content_length)
            metadata_record.content_type = metadata.get("content_type", metadata_record.content_type)
            metadata_record.content_hash = metadata.get("content_hash", metadata_record.content_hash)
            metadata_record.last_updated = datetime.utcnow() if any([
                metadata.get("etag"), 
                metadata.get("last_modified"),
                metadata.get("content_hash")
            ]) else metadata_record.last_updated
            metadata_record.last_checked = datetime.utcnow()
            
        db.commit()
        logger.info("Saved file metadata to database")
            
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving metadata: {str(e)}")
        raise Exception(f"Failed to save metadata: {str(e)}")

def download_efos_csv() -> Tuple[bytes, str]:
    """
    Downloads the EFOS CSV file from the SAT website with retry logic and chunked download
    
    Returns:
        Tuple with the content of the file in bytes and the filename
    """
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            logger.info(f"Downloading EFOS CSV from {EFOS_CSV_URL} (attempt {retry_count+1}/{MAX_RETRIES})")
            
            # Stream the download in chunks to handle large files
            response = requests.get(EFOS_CSV_URL, stream=True, timeout=300)  # 5-minute timeout
            response.raise_for_status()
            
            # Get the filename from the URL or use a default name
            filename = EFOS_CSV_URL.split("/")[-1]
            
            # Get total size for progress tracking
            total_size = int(response.headers.get('content-length', 0))
            total_size_mb = total_size / 1024 / 1024
            
            # Download in chunks
            chunks = []
            downloaded = 0
            start_time = time.time()
            
            for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                if chunk:  # filter out keep-alive chunks
                    chunks.append(chunk)
                    downloaded += len(chunk)
                    
                    # Log progress periodically (every ~5% or at least once if file is small)
                    if total_size > 0 and (downloaded % (max(total_size // 20, DOWNLOAD_CHUNK_SIZE * 100)) < DOWNLOAD_CHUNK_SIZE or downloaded == total_size):
                        percent = (downloaded / total_size) * 100
                        elapsed = time.time() - start_time
                        speed_mbps = (downloaded / 1024 / 1024) / elapsed if elapsed > 0 else 0
                        logger.info(f"Download progress: {percent:.1f}% ({downloaded/1024/1024:.2f}MB / {total_size_mb:.2f}MB) at {speed_mbps:.2f}MB/s")
            
            # Combine chunks
            content = b''.join(chunks)
            
            # Log download statistics
            download_time = time.time() - start_time
            download_speed = (len(content) / 1024 / 1024) / download_time if download_time > 0 else 0
            logger.info(f"Downloaded {len(content)/1024/1024:.2f}MB in {download_time:.2f} seconds ({download_speed:.2f}MB/s)")
            
            return content, filename
            
        except requests.RequestException as e:
            retry_count += 1
            if retry_count < MAX_RETRIES:
                wait_time = RETRY_BACKOFF * retry_count
                logger.warning(f"Error downloading EFOS CSV (attempt {retry_count}/{MAX_RETRIES}): {str(e)}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"Error downloading EFOS CSV after {MAX_RETRIES} attempts: {str(e)}")
                raise Exception(f"Failed to download EFOS CSV after {MAX_RETRIES} attempts: {str(e)}")

def clean_csv_data(csv_content: bytes) -> str:
    """
    Cleans the CSV content using the clean_csv.py script with improved error handling
    
    Args:
        csv_content: Raw CSV content in bytes
        
    Returns:
        Cleaned CSV content as string
    """
    input_path = None
    output_path = None
    
    try:
        # Create temporary files for input and output
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as input_file:
            input_file.write(csv_content)
            input_path = input_file.name
            
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as output_file:
            output_path = output_file.name
            
        # Use the clean_csv.py script using subprocess
        current_dir = os.path.dirname(os.path.abspath(__file__))
        clean_csv_script = os.path.join(current_dir, 'clean_csv.py')
        
        logger.info(f"Cleaning CSV data using {clean_csv_script}")
        
        # Set a timeout to prevent hanging processes
        result = subprocess.run(
            ['python', clean_csv_script, '-e', 'utf-8', '-o', output_path, input_path],
            capture_output=True,
            text=True,
            timeout=300  # 5-minute timeout
        )
        
        if result.returncode != 0:
            logger.error(f"Error running clean_csv.py: {result.stderr}")
            raise Exception(f"Failed to clean CSV: {result.stderr}")
        
        # Read cleaned CSV
        with open(output_path, 'r', encoding='utf-8') as f:
            cleaned_content = f.read()
            
        # Log cleaning statistics
        original_size = len(csv_content)
        cleaned_size = len(cleaned_content.encode('utf-8'))
        size_reduction = (1 - (cleaned_size / original_size)) * 100 if original_size > 0 else 0
        
        logger.info(f"Cleaned CSV data: {original_size/1024/1024:.2f}MB → {cleaned_size/1024/1024:.2f}MB ({size_reduction:.1f}% reduction)")
        
        return cleaned_content
        
    except Exception as e:
        logger.error(f"Error cleaning CSV data: {str(e)}")
        raise Exception(f"Failed to clean CSV data: {str(e)}")
    finally:
        # Clean up temporary files (even in case of errors)
        try:
            if input_path and os.path.exists(input_path):
                os.unlink(input_path)
        except Exception as e:
            logger.warning(f"Error deleting temporary input file: {str(e)}")
            
        try:
            if output_path and os.path.exists(output_path):
                os.unlink(output_path)
        except Exception as e:
            logger.warning(f"Error deleting temporary output file: {str(e)}")

def parse_csv_data(csv_content: str) -> List[Dict]:
    """
    Parses the cleaned CSV content into a list of dictionaries
    
    Args:
        csv_content: Cleaned CSV content as string
        
    Returns:
        List of dictionaries with the parsed data
    """
    try:
        logger.info("Parsing CSV data")
        records = []
        
        # Parse CSV with appropriate settings
        reader = csv.DictReader(
            io.StringIO(csv_content),
            delimiter=',',
            quotechar='"'
        )
        
        # Track parsing progress
        row_count = 0
        start_time = time.time()
        last_log_time = start_time
        
        for row in reader:
            # Convert keys to lowercase and replace spaces with underscores
            normalized_row = {}
            for key, value in row.items():
                if key:  # Skip empty keys
                    normalized_key = key.lower().replace(' ', '_').replace('.', '')
                    if normalized_key == 'no':
                        normalized_key = 'numero'
                    elif normalized_key == 'situación_del_contribuyente':
                        normalized_key = 'situacion_contribuyente'
                    elif normalized_key.startswith('número_y_fecha'):
                        # Handle special cases for column names
                        if 'presunción_sat' in normalized_key:
                            normalized_key = 'numero_fecha_oficio_global_presuncion_sat'
                        elif 'presunción_dof' in normalized_key:
                            normalized_key = 'numero_fecha_oficio_global_presuncion_dof'
                        elif 'desvirtuaron_sat' in normalized_key:
                            normalized_key = 'numero_fecha_oficio_global_contribuyentes_desvirtuaron_sat'
                        elif 'desvirtuaron_dof' in normalized_key:
                            normalized_key = 'numero_fecha_oficio_global_contribuyentes_desvirtuaron_dof'
                        elif 'definitivos_sat' in normalized_key:
                            normalized_key = 'numero_fecha_oficio_global_definitivos_sat'
                        elif 'definitivos_dof' in normalized_key:
                            normalized_key = 'numero_fecha_oficio_global_definitivos_dof'
                        elif 'sentencia_favorable_sat' in normalized_key:
                            normalized_key = 'numero_fecha_oficio_global_sentencia_favorable_sat'
                        elif 'sentencia_favorable_dof' in normalized_key:
                            normalized_key = 'numero_fecha_oficio_global_sentencia_favorable_dof'
                    elif normalized_key.startswith('publicación_'):
                        # Handle publication column names
                        if 'sat_presuntos' in normalized_key:
                            normalized_key = 'publicacion_pagina_sat_presuntos'
                        elif 'dof_presuntos' in normalized_key:
                            normalized_key = 'publicacion_dof_presuntos'
                        elif 'sat_desvirtuados' in normalized_key:
                            normalized_key = 'publicacion_pagina_sat_desvirtuados'
                        elif 'dof_desvirtuados' in normalized_key:
                            normalized_key = 'publicacion_dof_desvirtuados'
                        elif 'sat_definitivos' in normalized_key:
                            normalized_key = 'publicacion_pagina_sat_definitivos'
                        elif 'dof_definitivos' in normalized_key:
                            normalized_key = 'publicacion_dof_definitivos'
                        elif 'sat_sentencia_favorable' in normalized_key:
                            normalized_key = 'publicacion_pagina_sat_sentencia_favorable'
                        elif 'dof_sentencia_favorable' in normalized_key:
                            normalized_key = 'publicacion_dof_sentencia_favorable'
                    
                    # Store normalized value
                    normalized_row[normalized_key] = value.strip() if value else None
            
            records.append(normalized_row)
            row_count += 1
            
            # Log progress every 10 seconds or every 10,000 rows
            current_time = time.time()
            if row_count % 10000 == 0 or current_time - last_log_time >= 10:
                elapsed = current_time - start_time
                rate = row_count / elapsed if elapsed > 0 else 0
                logger.info(f"Parsed {row_count} records so far ({rate:.1f} records/sec)")
                last_log_time = current_time
        
        # Log final statistics
        elapsed = time.time() - start_time
        rate = row_count / elapsed if elapsed > 0 else 0
        logger.info(f"Parsed {len(records)} records in {elapsed:.2f} seconds ({rate:.1f} records/sec)")
        return records
    except Exception as e:
        logger.error(f"Error parsing CSV data: {str(e)}")
        logger.error(traceback.format_exc())
        raise Exception(f"Failed to parse CSV data: {str(e)}")

def chunk_records(records: List[Dict], chunk_size: int = IMPORT_BATCH_SIZE) -> Generator[List[Dict], None, None]:
    """
    Divides records into manageable chunks for batch processing
    
    Args:
        records: List of record dictionaries
        chunk_size: Number of records per chunk
        
    Yields:
        Chunks of records
    """
    for i in range(0, len(records), chunk_size):
        yield records[i:i + chunk_size]

def import_efos_data(db: Session, records: List[Dict]) -> int:
    """
    Imports the parsed EFOS records into the database with batch processing
    
    Args:
        db: Database session
        records: List of dictionaries with the parsed data
        
    Returns:
        Number of records imported
    """
    try:
        logger.info(f"Importing {len(records)} EFOS records into database")
        
        # First, check database size to ensure we're not exceeding limits
        check_database_size(db)
        
        # Remove existing records - we'll completely replace the data
        logger.info("Deleting existing records from database")
        db.execute(delete(EfosRecord))
        db.commit()
        logger.info("Existing records deleted")
        
        # Insert new records in batches
        total_count = 0
        start_time = time.time()
        
        # Process records in chunks to avoid memory issues
        for i, chunk in enumerate(chunk_records(records)):
            try:
                chunk_start = time.time()
                logger.info(f"Processing batch {i+1} ({len(chunk)} records)")
                
                # Create a list of EfosRecord objects for this chunk
                efos_records = []
                
                for record in chunk:
                    try:
                        # Convert numero to integer if possible
                        if 'numero' in record and record['numero']:
                            try:
                                record['numero'] = int(record['numero'])
                            except (ValueError, TypeError):
                                record['numero'] = None
                        
                        # Create EfosRecord object
                        efos_record = EfosRecord(
                            numero=record.get('numero'),
                            rfc=record.get('rfc', ''),
                            nombre_contribuyente=record.get('nombre_del_contribuyente', ''),
                            situacion_contribuyente=record.get('situacion_contribuyente'),
                            numero_fecha_oficio_global_presuncion_sat=record.get('numero_fecha_oficio_global_presuncion_sat'),
                            publicacion_pagina_sat_presuntos=record.get('publicacion_pagina_sat_presuntos'),
                            numero_fecha_oficio_global_presuncion_dof=record.get('numero_fecha_oficio_global_presuncion_dof'),
                            publicacion_dof_presuntos=record.get('publicacion_dof_presuntos'),
                            numero_fecha_oficio_global_contribuyentes_desvirtuaron_sat=record.get('numero_fecha_oficio_global_contribuyentes_desvirtuaron_sat'),
                            publicacion_pagina_sat_desvirtuados=record.get('publicacion_pagina_sat_desvirtuados'),
                            numero_fecha_oficio_global_contribuyentes_desvirtuaron_dof=record.get('numero_fecha_oficio_global_contribuyentes_desvirtuaron_dof'),
                            publicacion_dof_desvirtuados=record.get('publicacion_dof_desvirtuados'),
                            numero_fecha_oficio_global_definitivos_sat=record.get('numero_fecha_oficio_global_definitivos_sat'),
                            publicacion_pagina_sat_definitivos=record.get('publicacion_pagina_sat_definitivos'),
                            numero_fecha_oficio_global_definitivos_dof=record.get('numero_fecha_oficio_global_definitivos_dof'),
                            publicacion_dof_definitivos=record.get('publicacion_dof_definitivos'),
                            numero_fecha_oficio_global_sentencia_favorable_sat=record.get('numero_fecha_oficio_global_sentencia_favorable_sat'),
                            publicacion_pagina_sat_sentencia_favorable=record.get('publicacion_pagina_sat_sentencia_favorable'),
                            numero_fecha_oficio_global_sentencia_favorable_dof=record.get('numero_fecha_oficio_global_sentencia_favorable_dof'),
                            publicacion_dof_sentencia_favorable=record.get('publicacion_dof_sentencia_favorable'),
                        )
                        
                        efos_records.append(efos_record)
                            
                    except Exception as e:
                        logger.error(f"Error preparing record: {str(e)}")
                        logger.error(f"Problematic record: {record}")
                        # Continue with other records
                        continue
                
                # Bulk insert all records in this batch
                if efos_records:
                    db.bulk_save_objects(efos_records)
                    db.commit()
                    
                    total_count += len(efos_records)
                    
                    # Log processing statistics for this batch
                    chunk_time = time.time() - chunk_start
                    rate = len(efos_records) / chunk_time if chunk_time > 0 else 0
                    
                    logger.info(f"Batch {i+1} complete: {len(efos_records)} records in {chunk_time:.2f} seconds ({rate:.1f} records/sec)")
                    logger.info(f"Total progress: {total_count}/{len(records)} records ({total_count/len(records)*100:.1f}%)")
                    
                    # Explicitly clear the list to help with garbage collection
                    efos_records.clear()
                
            except Exception as e:
                db.rollback()
                logger.error(f"Error processing batch {i+1}: {str(e)}")
                logger.error(traceback.format_exc())
                # Continue with next batch
                continue
        
        # Final commit (although each batch already commits)
        db.commit()
        
        # Log final import statistics
        total_time = time.time() - start_time
        overall_rate = total_count / total_time if total_time > 0 else 0
        logger.info(f"Successfully imported {total_count} EFOS records in {total_time:.2f} seconds ({overall_rate:.1f} records/sec)")
        
        return total_count
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error importing EFOS data: {str(e)}")
        logger.error(traceback.format_exc())
        raise Exception(f"Failed to import EFOS data: {str(e)}")

def check_database_size(db: Session) -> None:
    """
    Checks the current database size against limits
    
    Args:
        db: Database session
        
    Raises:
        Exception if database is over the size limit
    """
    try:
        # For SQLite (approximate size by checking the file)
        from database import SQLALCHEMY_DATABASE_URL, USE_SQLITE
        
        if "sqlite" in SQLALCHEMY_DATABASE_URL and USE_SQLITE:
            # Extract file path from SQLite URL
            if SQLALCHEMY_DATABASE_URL.startswith("sqlite:///"):
                db_path = SQLALCHEMY_DATABASE_URL[10:]  # Remove sqlite:///
                if os.path.exists(db_path):
                    size_mb = os.path.getsize(db_path) / (1024 * 1024)
                    logger.info(f"Current SQLite database size: {size_mb:.2f}MB (limit: {MAX_DB_SIZE_MB}MB)")
                    
                    if size_mb > MAX_DB_SIZE_MB:
                        logger.warning(f"Database size ({size_mb:.2f}MB) exceeds limit ({MAX_DB_SIZE_MB}MB)")
                        # Continue anyway but log the warning
        
        # For PostgreSQL (can get size with an SQL query, but this is enough for Heroku)
        # Count the number of records as an indication of database size
        record_count = db.query(func.count(EfosRecord.id)).scalar()
        logger.info(f"Current EFOS record count: {record_count}")
        
    except Exception as e:
        logger.warning(f"Error checking database size: {str(e)}")
        # Do not raise an exception, just continue with the import

def update_efos_database(db: Session) -> Dict:
    """
    Complete workflow to update the EFOS database:
    1. Download the CSV file
    2. Check if it has changed since last update
    3. If changed, clean the CSV data, parse it, and import to database
    4. Update the file metadata
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with the results of the update
    """
    start_time = datetime.utcnow()
    logger.info("Starting EFOS database update check")
    
    try:
        # First, get file metadata to check if we need to download the whole file
        try:
            remote_metadata = get_file_metadata()
            
            # Check if we already have this version of the file
            metadata_record = db.query(EfosMetadata).first()
            
            if metadata_record and remote_metadata.get("etag") and metadata_record.etag == remote_metadata.get("etag"):
                # No change detected based on ETag, skip download
                logger.info("No changes detected based on ETag, skipping full download")
                
                end_time = datetime.utcnow()
                processing_time = (end_time - start_time).total_seconds()
                
                # Update last_checked in metadata
                metadata_record.last_checked = datetime.utcnow()
                db.commit()
                
                result = {
                    "status": "unchanged",
                    "message": "EFOS file has not changed since last update (based on ETag)",
                    "processing_time_seconds": processing_time,
                    "timestamp": end_time.isoformat()
                }
                
                logger.info(f"EFOS database update skipped (file unchanged) in {processing_time:.2f} seconds")
                return result
        except Exception as e:
            logger.warning(f"Error checking initial metadata, will proceed with full download: {str(e)}")
        
        # Download CSV
        try:
            csv_content, filename = download_efos_csv()
            logger.info(f"Downloaded {len(csv_content)} bytes from {filename}")
        except Exception as e:
            logger.error(f"Error downloading EFOS CSV: {str(e)}")
            raise
            
        # Check if file has changed
        has_changed, metadata = has_file_changed(db, csv_content)
        
        # If file has not changed, skip processing
        if not has_changed:
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            # Update last_checked in metadata
            save_metadata(db, metadata)
            
            result = {
                "status": "unchanged",
                "message": "EFOS file has not changed since last update",
                "processing_time_seconds": processing_time,
                "timestamp": end_time.isoformat()
            }
            
            logger.info(f"EFOS database update skipped (file unchanged) in {processing_time:.2f} seconds")
            return result
        
        # The file has changed, proceed with processing
        
        # Clean CSV
        try:
            cleaned_csv = clean_csv_data(csv_content)
            logger.info(f"Cleaned CSV data, size: {len(cleaned_csv)} characters")
            
            # Help garbage collection by deleting the raw content after cleaning
            del csv_content
            
        except Exception as e:
            logger.error(f"Error cleaning CSV: {str(e)}")
            raise
        
        # Parse CSV
        try:
            records = parse_csv_data(cleaned_csv)
            logger.info(f"Parsed {len(records)} records from CSV")
            
            # Help garbage collection
            del cleaned_csv
            
        except Exception as e:
            logger.error(f"Error parsing CSV: {str(e)}")
            raise
        
        # Import data
        try:
            imported_count = import_efos_data(db, records)
            
            # Help garbage collection
            del records
            
        except Exception as e:
            logger.error(f"Error importing data: {str(e)}")
            raise
        
        # Save file metadata
        save_metadata(db, metadata)
        
        # Calculate processing time
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        result = {
            "status": "success",
            "records_processed": len(records) if 'records' in locals() else 0,
            "records_imported": imported_count,
            "processing_time_seconds": processing_time,
            "timestamp": end_time.isoformat()
        }
        
        logger.info(f"EFOS database update completed successfully in {processing_time:.2f} seconds")
        return result
        
    except Exception as e:
        logger.error(f"Error in EFOS database update: {str(e)}")
        logger.error(traceback.format_exc())
        
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        error_result = {
            "status": "error",
            "error_message": str(e),
            "processing_time_seconds": processing_time,
            "timestamp": end_time.isoformat()
        }
        
        logger.error(f"EFOS database update failed: {str(e)}")
        return error_result

def check_rfc_in_efos(db: Session, rfc: str) -> Optional[Dict]:
    """
    Checks if a given RFC is in the EFOS database
    
    Args:
        db: Database session
        rfc: RFC to check
        
    Returns:
        Dictionary with the EFOS status or None if not found
    """
    try:
        # Query the database
        record = db.query(EfosRecord).filter(EfosRecord.rfc == rfc).first()
        
        if not record:
            return None
            
        # Return the record as a dictionary
        return {
            "rfc": record.rfc,
            "nombre_contribuyente": record.nombre_contribuyente,
            "situacion_contribuyente": record.situacion_contribuyente,
            "publicacion_sat_presuntos": record.publicacion_pagina_sat_presuntos,
            "publicacion_dof_presuntos": record.publicacion_dof_presuntos,
            "publicacion_sat_definitivos": record.publicacion_pagina_sat_definitivos,
            "publicacion_dof_definitivos": record.publicacion_dof_definitivos,
            "publicacion_sat_sentencia_favorable": record.publicacion_pagina_sat_sentencia_favorable,
            "publicacion_dof_sentencia_favorable": record.publicacion_dof_sentencia_favorable,
        }
        
    except Exception as e:
        logger.error(f"Error checking RFC in EFOS database: {str(e)}")
        return None 