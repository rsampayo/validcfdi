"""
XML Processing Routes

API endpoints for processing XML CFDI files.
"""
from fastapi import APIRouter, HTTPException, Depends, Body, File, UploadFile
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import base64
import os
import uuid
import logging

from api.auth.auth_handler import validate_api_token
from utils.cfdi_xml_parser import (
    extract_cfdi_data, 
    validate_cfdi_structure,
    get_verification_data
)
from api.services.sat_verification import verify_cfdi

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/xml",
    tags=["XML Processing"],
    dependencies=[Depends(validate_api_token)],
)

# Models
class XMLContentRequest(BaseModel):
    """Request model for XML content"""
    xml_content: str = Field(..., description="XML content as string or base64-encoded string")
    is_base64: bool = Field(False, description="Flag indicating if content is base64-encoded")

class XMLFileUploadResponse(BaseModel):
    """Response model for XML file upload"""
    filename: str
    size: int
    content_type: str
    verification_data: Dict[str, Any]
    parsed_data: Dict[str, Any]

class ProcessXMLResponse(BaseModel):
    """Response model for XML processing"""
    verification_data: Dict[str, Any]
    parsed_data: Dict[str, Any]
    sat_verification: Optional[Dict[str, Any]] = None

@router.post("/process", response_model=ProcessXMLResponse)
async def process_xml_content(request: XMLContentRequest):
    """
    Process XML content and return parsed data and verification results.
    """
    try:
        # Validate XML structure
        is_valid, error = validate_cfdi_structure(request.xml_content, request.is_base64)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid XML structure: {error}")
        
        # Extract data from XML
        parsed_data = extract_cfdi_data(request.xml_content, request.is_base64)
        verification_data = parsed_data.get("verification_data", {})
        
        # Verify with SAT
        sat_verification = {}
        if verification_data and all(verification_data.values()):
            sat_verification = await verify_cfdi(
                uuid=verification_data["uuid"], 
                emisor_rfc=verification_data["emisor_rfc"],
                receptor_rfc=verification_data["receptor_rfc"],
                total=verification_data["total"]
            )
        
        return {
            "verification_data": verification_data,
            "parsed_data": parsed_data,
            "sat_verification": sat_verification
        }
    
    except Exception as e:
        logger.error(f"Error processing XML: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing XML: {str(e)}")

@router.post("/upload", response_model=XMLFileUploadResponse)
async def upload_xml_file(file: UploadFile = File(...)):
    """
    Upload and process XML file.
    """
    try:
        # Check if file is an XML file
        if not file.filename.lower().endswith('.xml'):
            raise HTTPException(status_code=400, detail="Only XML files are accepted")
        
        # Read file content
        content = await file.read()
        xml_content = content.decode('utf-8')
        
        # Save file to temporary location (optional)
        temp_filename = f"temp_{uuid.uuid4()}.xml"
        temp_path = os.path.join("tests/xml_samples", temp_filename)
        with open(temp_path, "wb") as f:
            f.write(content)
        
        # Validate XML structure
        is_valid, error = validate_cfdi_structure(xml_content)
        if not is_valid:
            os.remove(temp_path)  # Clean up
            raise HTTPException(status_code=400, detail=f"Invalid XML structure: {error}")
        
        # Extract data from XML
        parsed_data = extract_cfdi_data(xml_content)
        verification_data = parsed_data.get("verification_data", {})
        
        return {
            "filename": file.filename,
            "size": len(content),
            "content_type": file.content_type,
            "verification_data": verification_data,
            "parsed_data": parsed_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@router.post("/verify-and-process", response_model=ProcessXMLResponse)
async def verify_and_process_xml(request: XMLContentRequest):
    """
    Verify CFDI with SAT and process XML content.
    """
    try:
        # Validate XML structure
        is_valid, error = validate_cfdi_structure(request.xml_content, request.is_base64)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid XML structure: {error}")
        
        # Extract data from XML
        parsed_data = extract_cfdi_data(request.xml_content, request.is_base64)
        verification_data = parsed_data.get("verification_data", {})
        
        # Verify with SAT if we have all required data
        sat_verification = {}
        if verification_data and all(k in verification_data and verification_data[k] for k in ["uuid", "emisor_rfc", "receptor_rfc", "total"]):
            sat_verification = await verify_cfdi(
                uuid=verification_data["uuid"], 
                emisor_rfc=verification_data["emisor_rfc"],
                receptor_rfc=verification_data["receptor_rfc"],
                total=verification_data["total"]
            )
        else:
            raise HTTPException(status_code=400, detail="Missing required verification data in XML")
        
        return {
            "verification_data": verification_data,
            "parsed_data": parsed_data,
            "sat_verification": sat_verification
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing XML: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing XML: {str(e)}")

@router.post("/extract-only", response_model=Dict[str, Any])
async def extract_xml_data(request: XMLContentRequest):
    """
    Extract data from XML without verification.
    """
    try:
        # Extract data from XML
        parsed_data = extract_cfdi_data(request.xml_content, request.is_base64)
        if "error" in parsed_data:
            raise HTTPException(status_code=400, detail=parsed_data["error"])
        
        return parsed_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting XML data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error extracting XML data: {str(e)}") 