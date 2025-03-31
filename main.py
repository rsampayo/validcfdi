from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from dotenv import load_dotenv

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
ENV = os.getenv("ENV", "development")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

# Create FastAPI application
app = FastAPI(
    title="Valid CFDI API",
    description="API for validating CFDIs and checking EFOS status",
    version=APP_VERSION,
)

# Add CORS middleware
allow_origins = [
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
app.include_router(xml_router)  # New XML routes

# Application startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the application."""
    logger.info(f"Starting Valid CFDI API in {ENV} environment")

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health():
    """Health check endpoint."""
    return {"status": "ok", "version": APP_VERSION}

# Error handler for unhandled exceptions
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    ) 