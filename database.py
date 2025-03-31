from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import Session
from typing import Generator, Optional
import os
from datetime import datetime
import uuid

# Database URL configuration
# By default use SQLite for local testing, PostgreSQL for production
USE_SQLITE: bool = os.environ.get("USE_SQLITE", "true").lower() == "true"

# Default URLs for different database types
DEFAULT_SQLITE_URL: str = "sqlite:///./cfdi_api.db"
DEFAULT_POSTGRES_URL: str = "postgresql://postgres:postgres@localhost:5432/cfdi_api"

# Choose which URL to use
if USE_SQLITE:
    SQLALCHEMY_DATABASE_URL: str = os.environ.get("DATABASE_URL", DEFAULT_SQLITE_URL)
    # Check if the URL was set to PostgreSQL but USE_SQLITE is true
    if SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
        SQLALCHEMY_DATABASE_URL = DEFAULT_SQLITE_URL
else:
    SQLALCHEMY_DATABASE_URL: str = os.environ.get("DATABASE_URL", DEFAULT_POSTGRES_URL)
    # Special handling for Heroku PostgreSQL URLs (they start with postgres://)
    if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Configure SQLAlchemy engine based on database type
if USE_SQLITE:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    print(f"Using SQLite database at: {SQLALCHEMY_DATABASE_URL}")
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    print(f"Using PostgreSQL database at: {SQLALCHEMY_DATABASE_URL.split('@')[1] if '@' in SQLALCHEMY_DATABASE_URL else SQLALCHEMY_DATABASE_URL}")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Model for API tokens
class ApiToken(Base):
    """
    Model for storing API authentication tokens.
    
    Attributes:
        id: Unique identifier for the token
        token: The actual token string used for authentication
        description: Optional description of what the token is for
        is_active: Whether the token is currently active and usable
        created_at: When the token was created
        updated_at: When the token was last updated
    """
    __tablename__ = "api_tokens"
    
    id: int = Column(Integer, primary_key=True, index=True)
    token: str = Column(String, unique=True, index=True, nullable=False)
    description: Optional[str] = Column(String, nullable=True)
    is_active: bool = Column(Boolean, default=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Model for superadmin users
class SuperAdmin(Base):
    """
    Model for storing superadmin user credentials.
    
    Attributes:
        id: Unique identifier for the superadmin
        username: Unique username for login
        hashed_password: Hashed password for authentication
        is_active: Whether the superadmin account is active
        created_at: When the account was created
        last_login: When the superadmin last logged in
    """
    __tablename__ = "superadmins"
    
    id: int = Column(Integer, primary_key=True, index=True)
    username: str = Column(String, unique=True, index=True, nullable=False)
    hashed_password: str = Column(String, nullable=False)
    is_active: bool = Column(Boolean, default=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    last_login: Optional[datetime] = Column(DateTime, nullable=True)

# Model for EFOS records (Empresas que Facturan Operaciones Simuladas)
class EfosRecord(Base):
    """
    Model for storing EFOS (Empresas que Facturan Operaciones Simuladas) records.
    
    These records contain information about companies identified by the SAT
    that may be issuing simulated operations.
    
    Attributes:
        id: Unique identifier for the record
        numero: Record number from SAT
        rfc: RFC (tax ID) of the company, indexed for fast lookups
        nombre_contribuyente: Name of the taxpayer (company)
        situacion_contribuyente: Current status of the taxpayer
        created_at: When the record was created in our database
        updated_at: When the record was last updated
    """
    __tablename__ = "efos_records"
    
    id: int = Column(Integer, primary_key=True, index=True)
    numero: Optional[int] = Column(Integer, nullable=True)
    rfc: str = Column(String, index=True, nullable=False)
    nombre_contribuyente: str = Column(String, nullable=False)
    situacion_contribuyente: Optional[str] = Column(String, nullable=True)
    numero_fecha_oficio_global_presuncion_sat: Optional[str] = Column(String, nullable=True)
    publicacion_pagina_sat_presuntos: Optional[str] = Column(String, nullable=True)
    numero_fecha_oficio_global_presuncion_dof: Optional[str] = Column(String, nullable=True)
    publicacion_dof_presuntos: Optional[str] = Column(String, nullable=True)
    numero_fecha_oficio_global_contribuyentes_desvirtuaron_sat: Optional[str] = Column(String, nullable=True)
    publicacion_pagina_sat_desvirtuados: Optional[str] = Column(String, nullable=True)
    numero_fecha_oficio_global_contribuyentes_desvirtuaron_dof: Optional[str] = Column(String, nullable=True)
    publicacion_dof_desvirtuados: Optional[str] = Column(String, nullable=True)
    numero_fecha_oficio_global_definitivos_sat: Optional[str] = Column(String, nullable=True)
    publicacion_pagina_sat_definitivos: Optional[str] = Column(String, nullable=True)
    numero_fecha_oficio_global_definitivos_dof: Optional[str] = Column(String, nullable=True)
    publicacion_dof_definitivos: Optional[str] = Column(String, nullable=True)
    numero_fecha_oficio_global_sentencia_favorable_sat: Optional[str] = Column(String, nullable=True)
    publicacion_pagina_sat_sentencia_favorable: Optional[str] = Column(String, nullable=True)
    numero_fecha_oficio_global_sentencia_favorable_dof: Optional[str] = Column(String, nullable=True)
    publicacion_dof_sentencia_favorable: Optional[str] = Column(String, nullable=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Model for EFOS file metadata tracking
class EfosMetadata(Base):
    """
    Model for tracking metadata about EFOS data files.
    
    This helps determine when the EFOS data was last updated and
    whether it needs to be refreshed.
    
    Attributes:
        id: Unique identifier for the metadata record
        etag: ETag from HTTP response for caching
        last_modified: Last-Modified HTTP header value
        content_length: Size of the content
        content_type: Type of the content
        content_hash: Hash of the content for detecting changes
        last_updated: When the EFOS data was last updated in our database
        last_checked: When we last checked for updates
        error_message: Any error message encountered during the last update attempt
    """
    __tablename__ = "efos_metadata"
    
    id: int = Column(Integer, primary_key=True, index=True)
    etag: Optional[str] = Column(String, nullable=True)
    last_modified: Optional[str] = Column(String, nullable=True)
    content_length: Optional[str] = Column(String, nullable=True)
    content_type: Optional[str] = Column(String, nullable=True)
    content_hash: Optional[str] = Column(String, nullable=True)
    last_updated: datetime = Column(DateTime, default=datetime.utcnow)
    last_checked: datetime = Column(DateTime, default=datetime.utcnow)
    error_message: Optional[str] = Column(Text, nullable=True)
    
def create_tables() -> None:
    """Create all database tables based on the defined models."""
    Base.metadata.create_all(bind=engine)

def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting a database session.
    
    Yields:
        A SQLAlchemy session that will be automatically closed when the request is complete.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 