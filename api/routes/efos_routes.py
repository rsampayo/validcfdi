"""
EFOS Check Routes

API endpoints for checking RFCs against the EFOS (Empresas que Facturan Operaciones Simuladas) list.
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from api.auth.auth_handler import validate_api_token
from api.services.efos_verification import check_rfc_in_efos, get_efos_metadata

# Create router
router = APIRouter(
    prefix="",
    tags=["EFOS Verification"],
    dependencies=[Depends(validate_api_token)],
)

# Models
class RfcCheckRequest(BaseModel):
    """Request model for RFC check"""
    rfc: str = Field(..., description="RFC to check", json_schema_extra={"example": "AAA100303L51"})
    
class RfcCheckResponse(BaseModel):
    """Response model for RFC check"""
    rfc: str
    is_in_efos_list: bool
    efos_data: Optional[Dict[str, Any]] = None
    efos_metadata: Optional[Dict[str, Any]] = None
    
class BatchRfcCheckRequest(BaseModel):
    """Request model for batch RFC check"""
    rfcs: List[str] = Field(..., description="List of RFCs to check", min_length=1)
    
class BatchRfcCheckResponse(BaseModel):
    """Response model for batch RFC check"""
    results: List[RfcCheckResponse]
    efos_metadata: Optional[Dict[str, Any]] = None

@router.post("/check-rfc-efos", response_model=RfcCheckResponse)
async def check_rfc_efos_endpoint(rfc_data: RfcCheckRequest):
    """
    Check if an RFC is in the EFOS list
    """
    try:
        # Get EFOS data for the RFC
        efos_data = await check_rfc_in_efos(rfc_data.rfc)
        
        # Get EFOS metadata
        metadata = await get_efos_metadata()
        
        return {
            "rfc": rfc_data.rfc,
            "is_in_efos_list": efos_data is not None,
            "efos_data": efos_data,
            "efos_metadata": metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking RFC: {str(e)}")

@router.post("/check-rfc-efos-batch", response_model=BatchRfcCheckResponse)
async def check_rfc_efos_batch_endpoint(batch_data: BatchRfcCheckRequest):
    """
    Check multiple RFCs against the EFOS list in a single request
    """
    try:
        results = []
        
        # Get EFOS metadata once for all checks
        metadata = await get_efos_metadata()
        
        # Process each RFC
        for rfc in batch_data.rfcs:
            # Get EFOS data for the RFC
            efos_data = await check_rfc_in_efos(rfc)
            
            results.append({
                "rfc": rfc,
                "is_in_efos_list": efos_data is not None,
                "efos_data": efos_data,
                "efos_metadata": None  # Include metadata at top level only
            })
        
        return {
            "results": results,
            "efos_metadata": metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking RFCs: {str(e)}") 