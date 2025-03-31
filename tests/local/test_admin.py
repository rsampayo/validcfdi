"""
Local Admin API tests for CFDI API
"""
import pytest
import requests
import os
import base64
from dotenv import load_dotenv
from base64 import b64encode

# Load environment variables from .env file
load_dotenv()

# API URL for local testing
API_URL = "http://localhost:8000"

# Get admin credentials from environment or use default
ADMIN_USERNAME = os.getenv("SUPERADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("SUPERADMIN_PASSWORD", "password")

@pytest.fixture
def admin_headers():
    """Create authentication headers for admin endpoints"""
    credentials = f"{ADMIN_USERNAME}:{ADMIN_PASSWORD}"
    encoded_credentials = b64encode(credentials.encode()).decode()
    return {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/json"
    }

@pytest.fixture
def token_id(admin_headers):
    """Create a test token and return its ID for testing"""
    # Create a token to use for testing
    response = requests.post(
        f"{API_URL}/admin/tokens",
        headers=admin_headers,
        json={"description": "Test Token for Fixture"}
    )
    
    # Ensure token was created successfully
    assert response.status_code == 200
    token_data = response.json()
    assert "id" in token_data
    
    # Return the token ID for other tests to use
    return token_data["id"]

def test_admin_list_tokens(admin_headers):
    """Test the admin/tokens endpoint (listing tokens)"""
    response = requests.get(
        f"{API_URL}/admin/tokens",
        headers=admin_headers
    )
    
    assert response.status_code == 200
    assert "tokens" in response.json()
    
def test_admin_efos_metadata(admin_headers):
    """Test the admin/efos/metadata endpoint"""
    response = requests.get(
        f"{API_URL}/admin/efos/metadata",
        headers=admin_headers
    )
    
    assert response.status_code == 200
    
def test_admin_create_token(admin_headers):
    """Test creating a new API token"""
    token_data = {
        "description": "Test token"
    }
    
    response = requests.post(
        f"{API_URL}/admin/tokens",
        headers=admin_headers,
        json=token_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "token" in data
    assert "description" in data
    assert data["description"] == token_data["description"]

def test_admin_regenerate_token(admin_headers, token_id):
    """Test token regeneration"""
    response = requests.post(
        f"{API_URL}/admin/tokens/{token_id}/regenerate",
        headers=admin_headers
    )
    
    assert response.status_code == 200
    assert "token" in response.json()
    
def test_admin_delete_token(admin_headers, token_id):
    """Test token deletion"""
    response = requests.delete(
        f"{API_URL}/admin/tokens/{token_id}",
        headers=admin_headers
    )
    
    assert response.status_code == 200
    assert "message" in response.json()

def test_admin_unauthorized_access():
    """Test unauthorized access to admin endpoints"""
    response = requests.get(f"{API_URL}/admin/tokens")
    
    assert response.status_code == 401
    assert "detail" in response.json()
    assert response.json()["detail"] == "Not authenticated" 