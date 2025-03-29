from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, Any, Optional, List
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
import asyncio
import concurrent.futures

# Load environment variables
load_dotenv()

# Import database and models
from database import get_db, create_tables
from security import verify_api_token, verify_superadmin
import token_manager
import admin_manager
from schemas import (
    TokenCreate, TokenUpdate, TokenResponse, TokenList, 
    SuperAdminCreate, SuperAdminUpdate, SuperAdminResponse,
    MessageResponse
)

# Initialize FastAPI app
app = FastAPI(
    title="CFDI Verification API",
    description="API para verificar la validez de Comprobantes Fiscales Digitales por Internet (CFDI)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Initialize security
token_auth = HTTPBearer()

# Get API token from environment variable or use default (for development only)
DEFAULT_API_TOKEN = os.environ.get("DEFAULT_API_TOKEN", "your-secret-token")

# Create initial superadmin if specified
SUPERADMIN_USERNAME = os.environ.get("SUPERADMIN_USERNAME")
SUPERADMIN_PASSWORD = os.environ.get("SUPERADMIN_PASSWORD")

# Models for CFDI request and response
class CFDIRequest(BaseModel):
    uuid: str = Field(..., description="UUID del CFDI", example="6128396f-c09b-4ec6-8699-43c5f7e3b230")
    emisor_rfc: str = Field(..., description="RFC del emisor", example="CDZ050722LA9")
    receptor_rfc: str = Field(..., description="RFC del receptor", example="XIN06112344A")
    total: str = Field(..., description="Monto total del CFDI", example="12000.00")
    
    class Config:
        json_schema_extra = {
            "example": {
                "uuid": "6128396f-c09b-4ec6-8699-43c5f7e3b230",
                "emisor_rfc": "CDZ050722LA9",
                "receptor_rfc": "XIN06112344A",
                "total": "12000.00"
            }
        }

class CFDIResponse(BaseModel):
    estado: Optional[str] = Field(None, description="Estado del CFDI")
    es_cancelable: Optional[str] = Field(None, description="Si el CFDI es cancelable")
    estatus_cancelacion: Optional[str] = Field(None, description="Estatus de cancelación")
    codigo_estatus: Optional[str] = Field(None, description="Código de estatus")
    validacion_efos: Optional[str] = Field(None, description="Validación EFOS")
    raw_response: Optional[str] = Field(None, description="Respuesta XML completa")
    
    class Config:
        json_schema_extra = {
            "example": {
                "estado": "Vigente",
                "es_cancelable": "Cancelable sin aceptación",
                "estatus_cancelacion": "No disponible",
                "codigo_estatus": "S - Comprobante obtenido satisfactoriamente.",
                "validacion_efos": "200",
                "raw_response": "<!-- XML response content -->"
            }
        }

class BatchCFDIRequest(BaseModel):
    cfdis: List[CFDIRequest] = Field(..., description="Lista de CFDIs a verificar", min_items=1)
    
    class Config:
        json_schema_extra = {
            "example": {
                "cfdis": [
                    {
                        "uuid": "6128396f-c09b-4ec6-8699-43c5f7e3b230",
                        "emisor_rfc": "CDZ050722LA9",
                        "receptor_rfc": "XIN06112344A",
                        "total": "12000.00"
                    },
                    {
                        "uuid": "9876543f-a01b-4ec6-8699-54c5f7e3b111",
                        "emisor_rfc": "ABC123456789",
                        "receptor_rfc": "XYZ987654321",
                        "total": "5000.00"
                    }
                ]
            }
        }

class CFDIBatchItem(BaseModel):
    request: CFDIRequest
    response: CFDIResponse
    error: Optional[str] = Field(None, description="Error message if validation failed")

class BatchCFDIResponse(BaseModel):
    results: List[CFDIBatchItem]
    
    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "request": {
                            "uuid": "6128396f-c09b-4ec6-8699-43c5f7e3b230",
                            "emisor_rfc": "CDZ050722LA9",
                            "receptor_rfc": "XIN06112344A",
                            "total": "12000.00"
                        },
                        "response": {
                            "estado": "Vigente",
                            "es_cancelable": "Cancelable sin aceptación",
                            "estatus_cancelacion": "No disponible",
                            "codigo_estatus": "S - Comprobante obtenido satisfactoriamente.",
                            "validacion_efos": "200"
                        },
                        "error": None
                    },
                    {
                        "request": {
                            "uuid": "invalid-uuid",
                            "emisor_rfc": "INVALID",
                            "receptor_rfc": "INVALID",
                            "total": "0.00"
                        },
                        "response": {},
                        "error": "Error during request to SAT service"
                    }
                ]
            }
        }

# CFDI verification function
def consult_cfdi(uuid: str, emisor_rfc: str, receptor_rfc: str, total: str) -> Dict[str, Any]:
    """
    Consulta el estatus de un CFDI en el servicio del SAT
    
    Args:
        uuid: UUID del CFDI
        emisor_rfc: RFC del emisor
        receptor_rfc: RFC del receptor
        total: Monto total del CFDI
        
    Returns:
        Diccionario con la información del estatus del CFDI
    """
    # Endpoint URL for the SAT CFDI consultation service
    url = "https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc"
    
    # Headers for the SOAP request
    headers = {
        'Content-Type': 'text/xml;charset=UTF-8',
        'SOAPAction': 'http://tempuri.org/IConsultaCFDIService/Consulta'
    }
    
    # SOAP envelope template
    soap_envelope = f'''
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
       <soap:Header/>
       <soap:Body>
          <tem:Consulta>
             <tem:expresionImpresa>?re={emisor_rfc}&amp;rr={receptor_rfc}&amp;tt={total}&amp;id={uuid}</tem:expresionImpresa>
          </tem:Consulta>
       </soap:Body>
    </soap:Envelope>
    '''
    
    result = {
        "estado": None,
        "es_cancelable": None, 
        "estatus_cancelacion": None,
        "codigo_estatus": None,
        "validacion_efos": None,
        "raw_response": None
    }
    
    # Send the SOAP request
    try:
        response = requests.post(url, headers=headers, data=soap_envelope.encode('utf-8'), timeout=10)
        
        # Parse the XML response
        if response.status_code == 200:
            # Save raw response
            result["raw_response"] = minidom.parseString(response.content).toprettyxml()
            
            try:
                # Parse the XML manually since namespaces can be complex in SOAP responses
                root = ET.fromstring(response.content)
                
                # Find direct paths by checking the XML structure
                for elem in root.findall(".//*"):
                    if '}' in elem.tag:  # Indicates a namespaced element
                        tag_name = elem.tag.split('}', 1)[1]  # Get tag name without namespace
                        if tag_name == 'CodigoEstatus':
                            result["codigo_estatus"] = elem.text
                        elif tag_name == 'EsCancelable':
                            result["es_cancelable"] = elem.text
                        elif tag_name == 'Estado':
                            result["estado"] = elem.text
                        elif tag_name == 'EstatusCancelacion':
                            result["estatus_cancelacion"] = elem.text if elem.text else "No disponible"
                        elif tag_name == 'ValidacionEFOS':
                            result["validacion_efos"] = elem.text
                
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error parsing XML response: {str(e)}"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error response from SAT service: {response.text}"
            )
            
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during request to SAT service: {str(e)}"
        )
        
    return result

# Startup event to create database tables and initial superadmin
@app.on_event("startup")
async def startup_event():
    create_tables()
    
    # Create default API token if it doesn't exist
    db = next(get_db())
    try:
        # Add default token if no tokens exist
        tokens = token_manager.get_all_tokens(db)
        if not tokens:
            token_manager.create_token(db, description="Default API token")
            
        # Create initial superadmin if credentials are provided
        if SUPERADMIN_USERNAME and SUPERADMIN_PASSWORD:
            try:
                admin_manager.create_superadmin(db, SUPERADMIN_USERNAME, SUPERADMIN_PASSWORD)
            except HTTPException:
                # Superadmin already exists, ignore
                pass
    finally:
        db.close()

# API Endpoints
@app.post("/verify-cfdi", response_model=CFDIResponse, tags=["CFDI"])
def verify_cfdi(
    cfdi_data: CFDIRequest, 
    token: str = Depends(verify_api_token)
):
    """
    Verifica la validez de un CFDI con el SAT
    
    Esta API consulta el servicio oficial del SAT para verificar el estatus de un CFDI.
    Requiere autenticación mediante Bearer token.
    
    Returns:
        CFDIResponse: Información sobre la validez del CFDI
    """
    result = consult_cfdi(
        cfdi_data.uuid,
        cfdi_data.emisor_rfc,
        cfdi_data.receptor_rfc,
        cfdi_data.total
    )
    
    return CFDIResponse(**result)

@app.post("/verify-cfdi-batch", response_model=BatchCFDIResponse, tags=["CFDI"])
async def verify_cfdi_batch(
    batch_data: BatchCFDIRequest,
    token: str = Depends(verify_api_token)
):
    """
    Verifica la validez de múltiples CFDIs con el SAT en una sola petición
    
    Esta API consulta el servicio oficial del SAT para verificar el estatus de múltiples CFDIs.
    Cada CFDI se procesa de forma independiente y los resultados se devuelven en un único response.
    Requiere autenticación mediante Bearer token.
    
    Returns:
        BatchCFDIResponse: Información sobre la validez de todos los CFDIs solicitados
    """
    results = []
    
    # Process CFDIs in parallel using a thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all CFDI validation tasks to the thread pool
        future_to_cfdi = {
            executor.submit(
                process_single_cfdi, 
                cfdi
            ): cfdi for cfdi in batch_data.cfdis
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_cfdi):
            cfdi = future_to_cfdi[future]
            result = future.result()
            results.append(result)
    
    return BatchCFDIResponse(results=results)

def process_single_cfdi(cfdi: CFDIRequest) -> CFDIBatchItem:
    """
    Process a single CFDI and handle any exceptions
    """
    try:
        result = consult_cfdi(
            cfdi.uuid,
            cfdi.emisor_rfc,
            cfdi.receptor_rfc,
            cfdi.total
        )
        return CFDIBatchItem(
            request=cfdi,
            response=CFDIResponse(**result),
            error=None
        )
    except HTTPException as e:
        # Handle HTTP exceptions from consult_cfdi function
        return CFDIBatchItem(
            request=cfdi,
            response=CFDIResponse(),
            error=e.detail
        )
    except Exception as e:
        # Handle any other unexpected errors
        return CFDIBatchItem(
            request=cfdi,
            response=CFDIResponse(),
            error=f"Unexpected error: {str(e)}"
        )

@app.get("/health", tags=["Health"])
def health_check():
    """
    Simple health check endpoint
    
    Permite verificar si el servicio está funcionando correctamente.
    Este endpoint no requiere autenticación.
    """
    return {"status": "healthy"}

# Token Management Endpoints (Superadmin only)
@app.post("/admin/tokens", response_model=TokenResponse, tags=["Admin"])
def create_api_token(
    token_data: TokenCreate,
    superadmin = Depends(verify_superadmin),
    db: Session = Depends(get_db)
):
    """
    Create a new API token
    
    Requires superadmin authentication using HTTP Basic auth.
    """
    return token_manager.create_token(db, token_data.description)

@app.get("/admin/tokens", response_model=TokenList, tags=["Admin"])
def list_api_tokens(
    skip: int = 0,
    limit: int = 100,
    superadmin = Depends(verify_superadmin),
    db: Session = Depends(get_db)
):
    """
    List all API tokens
    
    Requires superadmin authentication using HTTP Basic auth.
    """
    tokens = token_manager.get_all_tokens(db, skip, limit)
    return {"tokens": tokens, "total": len(tokens)}

@app.get("/admin/tokens/{token_id}", response_model=TokenResponse, tags=["Admin"])
def get_api_token(
    token_id: int,
    superadmin = Depends(verify_superadmin),
    db: Session = Depends(get_db)
):
    """
    Get a specific API token by ID
    
    Requires superadmin authentication using HTTP Basic auth.
    """
    token = token_manager.get_token_by_id(db, token_id)
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    return token

@app.put("/admin/tokens/{token_id}", response_model=TokenResponse, tags=["Admin"])
def update_api_token(
    token_id: int,
    token_data: TokenUpdate,
    superadmin = Depends(verify_superadmin),
    db: Session = Depends(get_db)
):
    """
    Update an API token
    
    Requires superadmin authentication using HTTP Basic auth.
    """
    return token_manager.update_token(db, token_id, token_data.description, token_data.is_active)

@app.delete("/admin/tokens/{token_id}", response_model=MessageResponse, tags=["Admin"])
def delete_api_token(
    token_id: int,
    superadmin = Depends(verify_superadmin),
    db: Session = Depends(get_db)
):
    """
    Delete an API token
    
    Requires superadmin authentication using HTTP Basic auth.
    """
    token_manager.delete_token(db, token_id)
    return {"message": "Token deleted successfully"}

@app.post("/admin/tokens/{token_id}/regenerate", response_model=TokenResponse, tags=["Admin"])
def regenerate_api_token(
    token_id: int,
    superadmin = Depends(verify_superadmin),
    db: Session = Depends(get_db)
):
    """
    Regenerate an API token
    
    Creates a new token value for the existing token ID.
    Requires superadmin authentication using HTTP Basic auth.
    """
    return token_manager.regenerate_token(db, token_id)

# Superadmin Management Endpoints (Superadmin only)
@app.post("/admin/superadmins", response_model=SuperAdminResponse, tags=["Admin"])
def create_new_superadmin(
    admin_data: SuperAdminCreate,
    superadmin = Depends(verify_superadmin),
    db: Session = Depends(get_db)
):
    """
    Create a new superadmin
    
    Requires existing superadmin authentication using HTTP Basic auth.
    """
    return admin_manager.create_superadmin(db, admin_data.username, admin_data.password)

@app.put("/admin/superadmins/{username}/password", response_model=MessageResponse, tags=["Admin"])
def update_admin_password(
    username: str,
    password_data: SuperAdminUpdate,
    superadmin = Depends(verify_superadmin),
    db: Session = Depends(get_db)
):
    """
    Update a superadmin's password
    
    Requires superadmin authentication using HTTP Basic auth.
    """
    admin_manager.update_superadmin_password(
        db, username, password_data.current_password, password_data.new_password
    )
    return {"message": "Password updated successfully"}

@app.delete("/admin/superadmins/{username}", response_model=MessageResponse, tags=["Admin"])
def deactivate_admin_account(
    username: str,
    superadmin = Depends(verify_superadmin),
    db: Session = Depends(get_db)
):
    """
    Deactivate a superadmin account
    
    Requires superadmin authentication using HTTP Basic auth.
    """
    admin_manager.deactivate_superadmin(db, username)
    return {"message": "Superadmin deactivated successfully"} 