"""
Local Admin API tests for CFDI API
"""
import pytest
import requests
import os
import base64
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API URL for local testing
API_URL = "http://localhost:8000"

# Get admin credentials from environment or use default
ADMIN_USERNAME = os.getenv("SUPERADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("SUPERADMIN_PASSWORD", "password")

@pytest.fixture
def admin_headers():
    """Return the headers for admin API requests with basic auth"""
    credentials = f"{ADMIN_USERNAME}:{ADMIN_PASSWORD}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json"
    }

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
    """Test token creation"""
    test_data = {
        "description": "Test Token"
    }
    
    response = requests.post(
        f"{API_URL}/admin/tokens",
        headers=admin_headers,
        json=test_data
    )
    
    assert response.status_code == 200
    assert "token" in response.json()
    assert "id" in response.json()
    assert response.json()["description"] == "Test Token"
    
    # Store the new token ID for cleanup in later tests
    return response.json()["id"]

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