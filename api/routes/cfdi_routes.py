"""
CFDI Verification Routes

API endpoints for CFDI verification with SAT.
"""
from fastapi import APIRouter, HTTPException, Depends, Body, status
from typing import Dict, Any, Optional, List, cast
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
    """
    Request model for CFDI verification
    
    Attributes:
        uuid: UUID of the CFDI document
        emisor_rfc: RFC (tax ID) of the issuer
        receptor_rfc: RFC (tax ID) of the receiver
        total: Total amount of the invoice
    """
    uuid: str = Field(
        ..., 
        description="UUID of the CFDI", 
        examples=["6128396f-c09b-4ec6-8699-43c5f7e3b230"]
    )
    emisor_rfc: str = Field(
        ..., 
        description="RFC of the emisor", 
        examples=["CDZ050722LA9"]
    )
    receptor_rfc: str = Field(
        ..., 
        description="RFC of the receptor", 
        examples=["XIN06112344A"]
    )
    total: str = Field(
        ..., 
        description="Total amount of the CFDI", 
        examples=["12000.00"]
    )

class CFDIBatchRequest(BaseModel):
    """
    Request model for batch CFDI verification
    
    Attributes:
        cfdis: List of CFDI requests to verify in batch
    """
    cfdis: List[CFDIRequest] = Field(
        ..., 
        description="List of CFDIs to verify", 
        min_length=1
    )
    
class CFDIResponse(BaseModel):
    """
    Response model for CFDI verification
    
    Attributes:
        estado: Status of the CFDI
        es_cancelable: Whether the CFDI can be canceled
        estatus_cancelacion: Status of cancellation
        codigo_estatus: Status code from SAT
        validacion_efos: EFOS validation result
        efos_emisor: EFOS information about the issuer
        efos_receptor: EFOS information about the receiver
        raw_response: Raw XML response from SAT
    """
    estado: Optional[str] = Field(None, description="Status of the CFDI")
    es_cancelable: Optional[str] = Field(None, description="Whether the CFDI can be canceled")
    estatus_cancelacion: Optional[str] = Field(None, description="Status of cancellation")
    codigo_estatus: Optional[str] = Field(None, description="Status code from SAT")
    validacion_efos: Optional[str] = Field(None, description="EFOS validation result")
    efos_emisor: Optional[Dict[str, Any]] = Field(None, description="EFOS information about the issuer")
    efos_receptor: Optional[Dict[str, Any]] = Field(None, description="EFOS information about the receiver")
    raw_response: Optional[str] = Field(None, description="Raw XML response from SAT")
    
class CFDIBatchItem(BaseModel):
    """
    Item model for batch CFDI verification response
    
    Attributes:
        request: The original CFDI verification request
        response: The verification response
        error: Any error message if verification failed
    """
    request: CFDIRequest = Field(..., description="Original CFDI verification request")
    response: CFDIResponse = Field(..., description="Verification response")
    error: Optional[str] = Field(None, description="Error message if verification failed")
    
class BatchCFDIResponse(BaseModel):
    """
    Response model for batch CFDI verification
    
    Attributes:
        results: List of batch verification results
    """
    results: List[CFDIBatchItem] = Field(..., description="List of verification results")

@router.post(
    "/verify-cfdi", 
    response_model=CFDIResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify a single CFDI with SAT",
    response_description="CFDI verification result from SAT"
)
async def verify_cfdi_endpoint(
    cfdi_data: CFDIRequest = Body(..., description="CFDI data to verify")
) -> Dict[str, Any]:
    """
    Verify a CFDI with SAT.
    
    This endpoint sends the CFDI data to the SAT verification service and returns the result.
    
    Args:
        cfdi_data: The CFDI data to verify
        
    Returns:
        The verification result from SAT
        
    Raises:
        HTTPException: If there's an error during verification
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error verifying CFDI: {str(e)}"
        )

@router.post(
    "/verify-cfdi-batch", 
    response_model=BatchCFDIResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify multiple CFDIs with SAT in a single request",
    response_description="Batch verification results"
)
async def verify_cfdi_batch_endpoint(
    batch_data: CFDIBatchRequest = Body(..., description="Batch of CFDI data to verify")
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Verify multiple CFDIs with SAT in a single request.
    
    This endpoint processes multiple CFDIs in one request and returns the results for each.
    If one CFDI verification fails, the others will still be processed.
    
    Args:
        batch_data: The batch of CFDI data to verify
        
    Returns:
        The verification results for each CFDI in the batch
    """
    results: List[Dict[str, Any]] = []
    
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