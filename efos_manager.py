import os
import requests
import io
import csv
import tempfile
import subprocess
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import delete
from typing import List, Dict, Optional, Tuple
import logging

from database import EfosRecord

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# URL of the EFOS CSV file from SAT
EFOS_CSV_URL = "http://omawww.sat.gob.mx/cifras_sat/Documents/Listado_Completo_69-B.csv"

def download_efos_csv() -> Tuple[bytes, str]:
    """
    Downloads the EFOS CSV file from the SAT website
    
    Returns:
        Tuple with the content of the file in bytes and the filename
    """
    try:
        logger.info(f"Downloading EFOS CSV from {EFOS_CSV_URL}")
        response = requests.get(EFOS_CSV_URL, timeout=30)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Get the filename from the URL or use a default name
        filename = EFOS_CSV_URL.split("/")[-1]
        
        return response.content, filename
    except requests.RequestException as e:
        logger.error(f"Error downloading EFOS CSV: {str(e)}")
        raise Exception(f"Failed to download EFOS CSV: {str(e)}")

def clean_csv_data(csv_content: bytes) -> str:
    """
    Cleans the CSV content using the clean_csv.py script
    
    Args:
        csv_content: Raw CSV content in bytes
        
    Returns:
        Cleaned CSV content as string
    """
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
        result = subprocess.run(
            ['python', clean_csv_script, '-e', 'utf-8', '-o', output_path, input_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Error running clean_csv.py: {result.stderr}")
            raise Exception(f"Failed to clean CSV: {result.stderr}")
        
        # Read cleaned CSV
        with open(output_path, 'r', encoding='utf-8') as f:
            cleaned_content = f.read()
            
        # Clean up temporary files
        os.unlink(input_path)
        os.unlink(output_path)
        
        return cleaned_content
    except Exception as e:
        logger.error(f"Error cleaning CSV data: {str(e)}")
        raise Exception(f"Failed to clean CSV data: {str(e)}")

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
        
        logger.info(f"Parsed {len(records)} records from CSV")
        return records
    except Exception as e:
        logger.error(f"Error parsing CSV data: {str(e)}")
        raise Exception(f"Failed to parse CSV data: {str(e)}")

def import_efos_data(db: Session, records: List[Dict]) -> int:
    """
    Imports the parsed EFOS records into the database
    
    Args:
        db: Database session
        records: List of dictionaries with the parsed data
        
    Returns:
        Number of records imported
    """
    try:
        logger.info(f"Importing {len(records)} EFOS records into database")
        
        # Remove existing records - we'll completely replace the data
        db.execute(delete(EfosRecord))
        db.commit()
        
        # Insert new records
        count = 0
        for record in records:
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
                
                db.add(efos_record)
                count += 1
                
                # Commit in batches to avoid memory issues
                if count % 1000 == 0:
                    db.commit()
                    logger.info(f"Imported {count} records so far")
                    
            except Exception as e:
                logger.error(f"Error importing record: {str(e)}")
                logger.error(f"Problematic record: {record}")
                # Continue with other records
                continue
        
        # Final commit for remaining records
        db.commit()
        logger.info(f"Successfully imported {count} EFOS records")
        return count
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error importing EFOS data: {str(e)}")
        raise Exception(f"Failed to import EFOS data: {str(e)}")

def update_efos_database(db: Session) -> Dict:
    """
    Complete workflow to update the EFOS database:
    1. Download the CSV file
    2. Clean the CSV data
    3. Parse the CSV data
    4. Import the records to the database
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with the results of the update
    """
    start_time = datetime.now()
    logger.info("Starting EFOS database update")
    
    try:
        # Download CSV
        csv_content, filename = download_efos_csv()
        logger.info(f"Downloaded {len(csv_content)} bytes from {filename}")
        
        # Clean CSV
        cleaned_csv = clean_csv_data(csv_content)
        logger.info(f"Cleaned CSV data, size: {len(cleaned_csv)} characters")
        
        # Parse CSV
        records = parse_csv_data(cleaned_csv)
        logger.info(f"Parsed {len(records)} records from CSV")
        
        # Import data
        imported_count = import_efos_data(db, records)
        
        # Calculate processing time
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        result = {
            "status": "success",
            "records_processed": len(records),
            "records_imported": imported_count,
            "processing_time_seconds": processing_time,
            "timestamp": end_time.isoformat()
        }
        
        logger.info(f"EFOS database update completed successfully in {processing_time:.2f} seconds")
        return result
        
    except Exception as e:
        end_time = datetime.now()
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