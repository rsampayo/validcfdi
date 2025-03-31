"""
Local API tests for CFDI API
"""
import pytest
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API URL for local testing
API_URL = "http://localhost:8000"

# Get API token from environment or use default
API_TOKEN = os.getenv("TEST_API_TOKEN", "test-api-token")

@pytest.fixture
def headers():
    """Return the headers for API requests"""
    return {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }

def test_health_endpoint():
    """Test the health endpoint"""
    response = requests.get(f"{API_URL}/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] in ["ok", "healthy"]
    
def test_verify_cfdi(headers):
    """Test the verify-cfdi endpoint"""
    # Test data
    test_data = {
        "uuid": "6128396f-c09b-4ec6-8699-43c5f7e3b230",
        "emisor_rfc": "CDZ050722LA9",
        "receptor_rfc": "XIN06112344A",
        "total": "12000.00"
    }
    
    response = requests.post(
        f"{API_URL}/verify-cfdi",
        headers=headers,
        json=test_data
    )
    
    assert response.status_code == 200
    assert "estado" in response.json()
    
def test_verify_cfdi_batch(headers):
    """Test the verify-cfdi-batch endpoint"""
    # Test data
    test_data = {
        "cfdis": [
            {
                "uuid": "6128396f-c09b-4ec6-8699-43c5f7e3b230",
                "emisor_rfc": "CDZ050722LA9",
                "receptor_rfc": "XIN06112344A",
                "total": "12000.00"
            },
            {
                "uuid": "6128396f-c09b-4ec6-8699-43c5f7e3b230",
                "emisor_rfc": "CDZ050722LA9",
                "receptor_rfc": "XIN06112344A",
                "total": "12000.00"
            }
        ]
    }
    
    response = requests.post(
        f"{API_URL}/verify-cfdi-batch",
        headers=headers,
        json=test_data
    )
    
    assert response.status_code == 200
    assert "results" in response.json()
    assert len(response.json()["results"]) == 2

def test_check_rfc_efos(headers):
    """Test the check-rfc-efos endpoint"""
    # Test data
    test_data = {
        "rfc": "AAA100303L51"
    }
    
    response = requests.post(
        f"{API_URL}/check-rfc-efos",
        headers=headers,
        json=test_data
    )
    
    assert response.status_code == 200
    assert "rfc" in response.json()
    assert "is_in_efos_list" in response.json()

def test_check_rfc_efos_batch(headers):
    """Test the check-rfc-efos-batch endpoint"""
    # Test data
    test_data = {
        "rfcs": ["AAA100303L51", "AAA120730823", "AAA121206EV5"]
    }
    
    response = requests.post(
        f"{API_URL}/check-rfc-efos-batch",
        headers=headers,
        json=test_data
    )
    
    assert response.status_code == 200
    assert "results" in response.json()
    assert len(response.json()["results"]) == 3

def test_unauthorized_access():
    """Test unauthorized access to protected endpoint"""
    # Test data
    test_data = {
        "uuid": "6128396f-c09b-4ec6-8699-43c5f7e3b230",
        "emisor_rfc": "CDZ050722LA9",
        "receptor_rfc": "XIN06112344A",
        "total": "12000.00"
    }
    
    response = requests.post(
        f"{API_URL}/verify-cfdi",
        json=test_data
    )
    
    assert response.status_code == 401
    assert "detail" in response.json()
    assert response.json()["detail"] == "Not authenticated" 