from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from datetime import datetime
import uuid

# Database URL configuration
# By default use SQLite for local testing, PostgreSQL for production
USE_SQLITE = os.environ.get("USE_SQLITE", "true").lower() == "true"

# Default URLs for different database types
DEFAULT_SQLITE_URL = "sqlite:///./cfdi_api.db"
DEFAULT_POSTGRES_URL = "postgresql://postgres:postgres@localhost:5432/cfdi_api"

# Choose which URL to use
if USE_SQLITE:
    SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_SQLITE_URL)
    # Check if the URL was set to PostgreSQL but USE_SQLITE is true
    if SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
        SQLALCHEMY_DATABASE_URL = DEFAULT_SQLITE_URL
else:
    SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_POSTGRES_URL)
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
    __tablename__ = "api_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Model for superadmin users
class SuperAdmin(Base):
    __tablename__ = "superadmins"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
# Function to create tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Function to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 