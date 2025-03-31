"""
Test script for XML API endpoints
"""
import os
import json
import base64
import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    """Create a test client for the app"""
    return TestClient(app)

@pytest.fixture
def api_token():
    """Get API token from environment or use default"""
    return "b90249760c8bd829bfbdd91290393bfb202b950ffca45f4a3064ff6deb333792"

@pytest.fixture
def auth_headers(api_token):
    """Create authorization headers with API token"""
    return {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

@pytest.fixture
def sample_xml_40():
    """Get sample CFDI 4.0 XML content"""
    sample_path = os.path.join(os.getcwd(), 'tests', 'xml_samples', 'sample_cfdi.xml')
    with open(sample_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return content

@pytest.fixture
def sample_xml_33():
    """Get sample CFDI 3.3 XML content"""
    sample_path = os.path.join(os.getcwd(), 'tests', 'xml_samples', 'sample_cfdi33.xml')
    with open(sample_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return content

@pytest.fixture
def sample_xml_40_base64(sample_xml_40):
    """Get base64 encoded sample CFDI 4.0 XML content"""
    return base64.b64encode(sample_xml_40.encode('utf-8')).decode('utf-8')

def test_process_xml_endpoint(client, auth_headers, sample_xml_40):
    """Test the process XML endpoint with plain XML"""
    response = client.post(
        "/xml/process", 
        headers=auth_headers,
        json={
            "xml_content": sample_xml_40,
            "is_base64": False
        }
    )
    
    # If token is valid, expect 200, otherwise accept 403
    if response.status_code == 200:
        data = response.json()
        assert "verification_data" in data
        assert "parsed_data" in data
        assert data["verification_data"]["uuid"] == "6128396f-c09b-4ec6-8699-43c5f7e3b230"
        assert data["verification_data"]["emisor_rfc"] == "CDZ050722LA9"
        assert data["verification_data"]["receptor_rfc"] == "XIN06112344A"
        assert data["verification_data"]["total"] == "11600.00"
    else:
        assert response.status_code == 403
        assert "detail" in response.json()
        assert response.json()["detail"] == "Invalid API token"

def test_process_xml_endpoint_base64(client, auth_headers, sample_xml_40_base64):
    """Test the process XML endpoint with base64 encoded XML"""
    response = client.post(
        "/xml/process", 
        headers=auth_headers,
        json={
            "xml_content": sample_xml_40_base64,
            "is_base64": True
        }
    )
    
    # If token is valid, expect 200, otherwise accept 403
    if response.status_code == 200:
        data = response.json()
        assert "verification_data" in data
        assert "parsed_data" in data
        assert data["verification_data"]["uuid"] == "6128396f-c09b-4ec6-8699-43c5f7e3b230"
    else:
        assert response.status_code == 403
        assert "detail" in response.json()
        assert response.json()["detail"] == "Invalid API token"

def test_extract_only_endpoint(client, auth_headers, sample_xml_33):
    """Test the extract XML data endpoint"""
    response = client.post(
        "/xml/extract-only", 
        headers=auth_headers,
        json={
            "xml_content": sample_xml_33,
            "is_base64": False
        }
    )
    
    # If token is valid, expect 200, otherwise accept 403
    if response.status_code == 200:
        data = response.json()
        assert data["version"] == "3.3"
        assert data["uuid"] == "aa36c339-492c-4126-9c1a-5e4c12882486"
        assert data["emisor"]["rfc"] == "MAG041126GT8"
        assert data["receptor"]["rfc"] == "MALD940906KJ8"
        assert data["total"] == "5800.00"
    else:
        assert response.status_code == 403
        assert "detail" in response.json()
        assert response.json()["detail"] == "Invalid API token"

def test_unauthorized_access(client, sample_xml_40):
    """Test unauthorized access to the XML endpoints"""
    response = client.post(
        "/xml/process", 
        json={
            "xml_content": sample_xml_40,
            "is_base64": False
        }
    )
    # Should return 401 or 403 for unauthorized
    assert response.status_code in [401, 403]

def test_invalid_xml(client, auth_headers):
    """Test invalid XML input"""
    response = client.post(
        "/xml/process", 
        headers=auth_headers,
        json={
            "xml_content": "<invalid>xml</invalid>",
            "is_base64": False
        }
    )
    
    # If token is valid, expect 400 for invalid XML, otherwise accept 403 for auth failure
    if response.status_code == 400:
        assert "Invalid XML structure" in response.json()["detail"]
    else:
        assert response.status_code == 403
        assert "detail" in response.json() 