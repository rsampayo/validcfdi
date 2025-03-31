"""
Valid CFDI API - Main Application

This is the main entry point for the Valid CFDI API application.
It configures the FastAPI application, middleware, and includes all routers.
"""
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from typing import List, Dict, Any, AsyncGenerator
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from api.routes.cfdi_routes import router as cfdi_router
from api.routes.efos_routes import router as efos_router
from api.routes.admin_routes import router as admin_router
from api.routes.xml_routes import router as xml_router

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get environment variables
ENV: str = os.getenv("ENV", "development")
APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")

# Define lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Initialize the application on startup and cleanup on shutdown.
    
    Args:
        app: The FastAPI application instance
        
    Yields:
        None
    """
    # Startup
    logger.info(f"Starting Valid CFDI API in {ENV} environment")
    yield
    # Shutdown
    logger.info("Shutting down Valid CFDI API")

# Create FastAPI application
app = FastAPI(
    title="Valid CFDI API",
    description="API for validating CFDIs and checking EFOS status",
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware
allow_origins: List[str] = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "https://validcfdi.com.mx",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(cfdi_router)
app.include_router(efos_router)
app.include_router(admin_router)
app.include_router(xml_router)  # XML routes

# Health check endpoint
@app.get(
    "/health", 
    tags=["Health"],
    summary="Health check endpoint",
    description="Use this endpoint to check if the API is running correctly",
    status_code=status.HTTP_200_OK,
    response_description="Health status and version information"
)
async def health() -> Dict[str, str]:
    """
    Health check endpoint.
    
    Returns:
        A dictionary with the status and version of the application
    """
    return {"status": "ok", "version": APP_VERSION}

# Error handler for unhandled exceptions
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unhandled exceptions.
    
    Args:
        request: The request that caused the exception
        exc: The exception that was raised
        
    Returns:
        A JSON response with the error details
    """
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    ) 