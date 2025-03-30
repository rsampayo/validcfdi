from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
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
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.exc import SQLAlchemyError

# Load environment variables
load_dotenv()

# Import database and models
from database import get_db, create_tables, SessionLocal, EfosMetadata
from security import verify_api_token, verify_superadmin
import token_manager
import admin_manager
import efos_manager
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
    efos_emisor: Optional[Dict[str, Any]] = Field(None, description="Información de EFOS para el emisor")
    efos_receptor: Optional[Dict[str, Any]] = Field(None, description="Información de EFOS para el receptor")
    raw_response: Optional[str] = Field(None, description="Respuesta XML completa")
    
    class Config:
        json_schema_extra = {
            "example": {
                "estado": "Vigente",
                "es_cancelable": "Cancelable sin aceptación",
                "estatus_cancelacion": "No disponible",
                "codigo_estatus": "S - Comprobante obtenido satisfactoriamente.",
                "validacion_efos": "200",
                "efos_emisor": None,
                "efos_receptor": None,
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
                            "validacion_efos": "200",
                            "efos_emisor": None,
                            "efos_receptor": None
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

# Models for EFOS endpoints
class RfcCheckRequest(BaseModel):
    rfc: str = Field(..., description="RFC a consultar", example="XYZ123456789")

class RfcCheckResponse(BaseModel):
    rfc: str = Field(..., description="RFC consultado")
    is_in_efos_list: bool = Field(..., description="Indica si el RFC está en la lista EFOS")
    efos_data: Optional[Dict[str, Any]] = Field(None, description="Datos EFOS del RFC (si está en la lista)")
    efos_metadata: Optional[Dict[str, Any]] = Field(None, description="Información sobre la última actualización de la base de datos EFOS")

class BatchRfcCheckRequest(BaseModel):
    rfcs: List[str] = Field(..., description="Lista de RFCs a consultar", min_items=1, example=["XYZ123456789", "ABC987654321"])

class BatchRfcCheckResponse(BaseModel):
    results: List[RfcCheckResponse] = Field(..., description="Resultados de la consulta de cada RFC")
    efos_metadata: Optional[Dict[str, Any]] = Field(None, description="Información sobre la última actualización de la base de datos EFOS")

class EfosUpdateResponse(BaseModel):
    status: str = Field(..., description="Estado de la actualización")
    message: str = Field(..., description="Mensaje de la actualización")
    details: Optional[Dict[str, Any]] = Field(None, description="Detalles de la actualización")

# CFDI verification function
def consult_cfdi(uuid: str, emisor_rfc: str, receptor_rfc: str, total: str, db: Session = None) -> Dict[str, Any]:
    """
    Consulta el estatus de un CFDI en el servicio del SAT
    
    Args:
        uuid: UUID del CFDI
        emisor_rfc: RFC del emisor
        receptor_rfc: RFC del receptor
        total: Monto total del CFDI
        db: Optional database session for EFOS validation
        
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
        "efos_emisor": None,
        "efos_receptor": None,
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
                
                # Check EFOS status if database session is provided
                if db:
                    # Check emisor RFC in EFOS list
                    emisor_efos = efos_manager.check_rfc_in_efos(db, emisor_rfc)
                    if emisor_efos:
                        result["efos_emisor"] = emisor_efos
                        
                    # Check receptor RFC in EFOS list
                    receptor_efos = efos_manager.check_rfc_in_efos(db, receptor_rfc)
                    if receptor_efos:
                        result["efos_receptor"] = receptor_efos
                
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
            token_manager.create_token(db, TokenCreate(
                description="Default API Token",
                token=DEFAULT_API_TOKEN
            ))
            print("Created default API token")
            
        # Add superadmin if specified in environment variables
        if SUPERADMIN_USERNAME and SUPERADMIN_PASSWORD:
            admin = admin_manager.get_superadmin_by_username(db, SUPERADMIN_USERNAME)
            if not admin:
                admin_manager.create_superadmin(db, SuperAdminCreate(
                    username=SUPERADMIN_USERNAME,
                    password=SUPERADMIN_PASSWORD
                ))
                print(f"Created superadmin user: {SUPERADMIN_USERNAME}")
    finally:
        db.close()

# CFDI verification endpoint
@app.post("/verify-cfdi", response_model=CFDIResponse, tags=["CFDI"])
def verify_cfdi(
    cfdi_data: CFDIRequest, 
    token: str = Depends(verify_api_token),
    db: Session = Depends(get_db)
):
    """
    Verifica la validez de un CFDI consultando el servicio del SAT
    """
    try:
        result = consult_cfdi(
            cfdi_data.uuid, 
            cfdi_data.emisor_rfc, 
            cfdi_data.receptor_rfc, 
            cfdi_data.total,
            db
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# CFDI batch verification endpoint
@app.post("/verify-cfdi-batch", response_model=BatchCFDIResponse, tags=["CFDI"])
async def verify_cfdi_batch(
    batch_data: BatchCFDIRequest,
    token: str = Depends(verify_api_token),
    db: Session = Depends(get_db)
):
    """
    Verifica la validez de múltiples CFDIs consultando el servicio del SAT
    """
    # Limit the number of concurrent requests
    MAX_WORKERS = os.environ.get("MAX_WORKERS", 5)
    
    # Results will be stored here
    results = []
    
    # Process CFDIs in batches
    with concurrent.futures.ThreadPoolExecutor(max_workers=int(MAX_WORKERS)) as executor:
        # Create future objects for each CFDI request
        future_to_cfdi = {
            executor.submit(process_single_cfdi, cfdi, db): cfdi 
            for cfdi in batch_data.cfdis
        }
        
        # Wait for all futures to complete
        for future in concurrent.futures.as_completed(future_to_cfdi):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                cfdi = future_to_cfdi[future]
                results.append(CFDIBatchItem(
                    request=cfdi,
                    response=CFDIResponse(),
                    error=str(e)
                ))
    
    return BatchCFDIResponse(results=results)

# Helper function to process a single CFDI in the batch
def process_single_cfdi(cfdi: CFDIRequest, db: Session = None) -> CFDIBatchItem:
    """Process a single CFDI and return the result"""
    try:
        result = consult_cfdi(
            cfdi.uuid, 
            cfdi.emisor_rfc, 
            cfdi.receptor_rfc, 
            cfdi.total,
            db
        )
        
        return CFDIBatchItem(
            request=cfdi,
            response=CFDIResponse(**result),
            error=None
        )
    except Exception as e:
        # Return the error
        return CFDIBatchItem(
            request=cfdi,
            response=CFDIResponse(),
            error=str(e)
        )

# Health check endpoint
@app.get("/health", tags=["Health"])
def health_check():
    """
    Simple health check endpoint to verify the API is running
    """
    return {
        "status": "ok",
        "version": app.version
    }

# EFOS check endpoint
@app.post("/check-rfc-efos", response_model=RfcCheckResponse, tags=["EFOS"])
def check_rfc_efos(
    rfc_data: RfcCheckRequest,
    token: str = Depends(verify_api_token),
    db: Session = Depends(get_db)
):
    """
    Verifica si un RFC está en la lista de EFOS del SAT
    """
    try:
        # Check if RFC is in EFOS list
        efos_data = efos_manager.check_rfc_in_efos(db, rfc_data.rfc)
        
        # Get EFOS metadata
        metadata_record = db.query(EfosMetadata).first()
        efos_metadata = None
        
        if metadata_record:
            efos_metadata = {
                "last_updated": metadata_record.last_updated,
                "last_checked": metadata_record.last_checked,
                "etag": metadata_record.etag,
                "last_modified": metadata_record.last_modified,
                "content_hash": metadata_record.content_hash
            }
        
        return {
            "rfc": rfc_data.rfc,
            "is_in_efos_list": efos_data is not None,
            "efos_data": efos_data,
            "efos_metadata": efos_metadata
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking RFC in EFOS list: {str(e)}"
        )

# EFOS batch check endpoint
@app.post("/check-rfc-efos-batch", response_model=BatchRfcCheckResponse, tags=["EFOS"])
def check_rfc_efos_batch(
    batch_data: BatchRfcCheckRequest,
    token: str = Depends(verify_api_token),
    db: Session = Depends(get_db)
):
    """
    Verifica si múltiples RFCs están en la lista de EFOS del SAT
    """
    try:
        results = []
        
        # Get EFOS metadata once for the whole batch
        metadata_record = db.query(EfosMetadata).first()
        efos_metadata = None
        
        if metadata_record:
            efos_metadata = {
                "last_updated": metadata_record.last_updated,
                "last_checked": metadata_record.last_checked,
                "etag": metadata_record.etag,
                "last_modified": metadata_record.last_modified,
                "content_hash": metadata_record.content_hash
            }
        
        # Process each RFC
        for rfc in batch_data.rfcs:
            # Check if RFC is in EFOS list
            efos_data = efos_manager.check_rfc_in_efos(db, rfc)
            
            # Add result
            results.append({
                "rfc": rfc,
                "is_in_efos_list": efos_data is not None,
                "efos_data": efos_data,
                "efos_metadata": None  # Include metadata at the top level only
            })
        
        return {
            "results": results,
            "efos_metadata": efos_metadata
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking RFCs in EFOS list: {str(e)}"
        )

# EFOS database update endpoint
@app.post("/update-efos-database", response_model=EfosUpdateResponse, tags=["EFOS"])
def update_efos_database(
    background_tasks: BackgroundTasks,
    run_in_background: bool = True,
    superadmin = Depends(verify_superadmin),
    db: Session = Depends(get_db)
):
    """
    Actualiza la base de datos de EFOS descargando el archivo CSV del SAT
    
    El proceso puede ejecutarse en segundo plano o en primer plano.
    """
    try:
        if run_in_background:
            # Schedule update in background
            background_tasks.add_task(efos_manager.update_efos_database, db)
            return {
                "status": "processing",
                "message": "EFOS database update started in background",
                "details": None
            }
        else:
            # Run update in foreground
            result = efos_manager.update_efos_database(db)
            
            status_msg = "success" if result.get("status") == "success" else "error"
            message = (
                f"EFOS database updated successfully. Imported {result.get('records_imported', 0)} records."
                if status_msg == "success"
                else f"Error updating EFOS database: {result.get('error_message', 'Unknown error')}"
            )
            
            return {
                "status": status_msg,
                "message": message,
                "details": result
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating EFOS database: {str(e)}"
        )

# Admin token endpoints
@app.post("/admin/tokens", response_model=TokenResponse, tags=["Admin"])
def create_api_token(
    token_data: TokenCreate,
    superadmin = Depends(verify_superadmin),
    db: Session = Depends(get_db)
):
    """
    Create a new API token
    """
    try:
        return token_manager.create_token(db, token_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@app.get("/admin/tokens", response_model=TokenList, tags=["Admin"])
def list_api_tokens(
    skip: int = 0,
    limit: int = 100,
    superadmin = Depends(verify_superadmin),
    db: Session = Depends(get_db)
):
    """
    List all API tokens
    """
    tokens = token_manager.get_all_tokens(db, skip, limit)
    return {
        "tokens": tokens,
        "total": len(tokens)
    }

@app.get("/admin/tokens/{token_id}", response_model=TokenResponse, tags=["Admin"])
def get_api_token(
    token_id: int,
    superadmin = Depends(verify_superadmin),
    db: Session = Depends(get_db)
):
    """
    Get a specific API token by ID
    """
    token = token_manager.get_token_by_id(db, token_id)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )
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
    """
    updated_token = token_manager.update_token(db, token_id, token_data)
    if not updated_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )
    return updated_token

@app.delete("/admin/tokens/{token_id}", response_model=MessageResponse, tags=["Admin"])
def delete_api_token(
    token_id: int,
    superadmin = Depends(verify_superadmin),
    db: Session = Depends(get_db)
):
    """
    Delete an API token
    """
    result = token_manager.delete_token(db, token_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )
    return {"message": "Token deleted successfully"}

@app.post("/admin/tokens/{token_id}/regenerate", response_model=TokenResponse, tags=["Admin"])
def regenerate_api_token(
    token_id: int,
    superadmin = Depends(verify_superadmin),
    db: Session = Depends(get_db)
):
    """
    Regenerate an API token (create a new token value)
    """
    regenerated_token = token_manager.regenerate_token(db, token_id)
    if not regenerated_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )
    return regenerated_token

@app.post("/admin/superadmins", response_model=SuperAdminResponse, tags=["Admin"])
def create_new_superadmin(
    admin_data: SuperAdminCreate,
    superadmin = Depends(verify_superadmin),
    db: Session = Depends(get_db)
):
    """
    Create a new superadmin user
    """
    try:
        return admin_manager.create_superadmin(db, admin_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@app.put("/admin/superadmins/{username}/password", response_model=MessageResponse, tags=["Admin"])
def update_admin_password(
    username: str,
    password_data: SuperAdminUpdate,
    superadmin = Depends(verify_superadmin),
    db: Session = Depends(get_db)
):
    """
    Update a superadmin's password
    """
    result = admin_manager.update_superadmin_password(db, username, password_data.password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Superadmin not found"
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
    """
    result = admin_manager.deactivate_superadmin(db, username)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Superadmin not found"
        )
    return {"message": "Superadmin deactivated successfully"} 