"""
CFDI Verification Routes

API endpoints for CFDI verification with SAT.
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from api.auth.auth_handler import validate_api_token
from api.services.sat_verification import verify_cfdi

# Create router
router = APIRouter(
    prefix="",
    tags=["CFDI Verification"],
    dependencies=[Depends(validate_api_token)],
)

# Models
class CFDIRequest(BaseModel):
    """Request model for CFDI verification"""
    uuid: str = Field(..., description="UUID of the CFDI", json_schema_extra={"example": "6128396f-c09b-4ec6-8699-43c5f7e3b230"})
    emisor_rfc: str = Field(..., description="RFC of the emisor", json_schema_extra={"example": "CDZ050722LA9"})
    receptor_rfc: str = Field(..., description="RFC of the receptor", json_schema_extra={"example": "XIN06112344A"})
    total: str = Field(..., description="Total amount of the CFDI", json_schema_extra={"example": "12000.00"})

class CFDIBatchRequest(BaseModel):
    """Request model for batch CFDI verification"""
    cfdis: List[CFDIRequest] = Field(..., description="List of CFDIs to verify", min_length=1)
    
class CFDIResponse(BaseModel):
    """Response model for CFDI verification"""
    estado: Optional[str] = None
    es_cancelable: Optional[str] = None
    estatus_cancelacion: Optional[str] = None
    codigo_estatus: Optional[str] = None
    validacion_efos: Optional[str] = None
    efos_emisor: Optional[Dict[str, Any]] = None
    efos_receptor: Optional[Dict[str, Any]] = None
    raw_response: Optional[str] = None
    
class CFDIBatchItem(BaseModel):
    """Item model for batch CFDI verification response"""
    request: CFDIRequest
    response: CFDIResponse
    error: Optional[str] = None
    
class BatchCFDIResponse(BaseModel):
    """Response model for batch CFDI verification"""
    results: List[CFDIBatchItem]

@router.post("/verify-cfdi", response_model=CFDIResponse)
async def verify_cfdi_endpoint(cfdi_data: CFDIRequest):
    """
    Verify a CFDI with SAT
    """
    try:
        # Call the verify_cfdi service
        result = await verify_cfdi(
            uuid=cfdi_data.uuid,
            emisor_rfc=cfdi_data.emisor_rfc,
            receptor_rfc=cfdi_data.receptor_rfc,
            total=cfdi_data.total
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying CFDI: {str(e)}")

@router.post("/verify-cfdi-batch", response_model=BatchCFDIResponse)
async def verify_cfdi_batch_endpoint(batch_data: CFDIBatchRequest):
    """
    Verify multiple CFDIs with SAT in a single request
    """
    results = []
    
    # Process each CFDI individually
    for cfdi in batch_data.cfdis:
        try:
            result = await verify_cfdi(
                uuid=cfdi.uuid,
                emisor_rfc=cfdi.emisor_rfc,
                receptor_rfc=cfdi.receptor_rfc,
                total=cfdi.total
            )
            
            results.append({
                "request": cfdi,
                "response": result,
                "error": None
            })
        except Exception as e:
            results.append({
                "request": cfdi,
                "response": CFDIResponse(),
                "error": str(e)
            })
    
    return {"results": results} 