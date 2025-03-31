"""
Heroku API tests for CFDI API
"""
import pytest
import requests
import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API URL for Heroku testing
if len(sys.argv) > 1:
    # Allow passing API URL as command line argument
    API_URL = sys.argv[1]
else:
    API_URL = os.getenv("HEROKU_API_URL", "https://validcfdi-api-be42092ab7e2.herokuapp.com")

# Get API token from environment or use default
API_TOKEN = os.getenv("HEROKU_API_TOKEN", "c822cf5ee82316013d21d912d95c5a770f86bd4ed278a8a33e729609e387efa4")

@pytest.fixture
def headers():
    """Return the headers for API requests"""
    return {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }

def test_health_endpoint():
    """Test the health endpoint"""
    print(f"\nTesting Health Endpoint on {API_URL}...")
    
    response = requests.get(f"{API_URL}/health")
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 200
    assert "status" in response.json()
    
def test_verify_cfdi(headers):
    """Test the verify-cfdi endpoint"""
    print(f"\nTesting Single CFDI Verification on {API_URL}...")
    
    # Test data
    test_data = {
        "uuid": "6128396f-c09b-4ec6-8699-43c5f7e3b230",
        "emisor_rfc": "CDZ050722LA9",
        "receptor_rfc": "XIN06112344A",
        "total": "12000.00"
    }
    
    print("Request:")
    print(json.dumps(test_data, indent=2))
    
    response = requests.post(
        f"{API_URL}/verify-cfdi",
        headers=headers,
        json=test_data
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        response_data = response.json()
        # Truncate raw_response for better readability
        if "raw_response" in response_data:
            response_data["raw_response"] = response_data["raw_response"][:100] + "... (truncated)"
        print("Response:")
        print(json.dumps(response_data, indent=2))
    else:
        print(f"Error Response: {response.text}")
        
    assert response.status_code == 200
    assert "estado" in response.json()
    
def test_verify_cfdi_batch(headers):
    """Test the verify-cfdi-batch endpoint"""
    print(f"\nTesting Batch CFDI Verification on {API_URL}...")
    
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
    
    print("Request:")
    print(json.dumps(test_data, indent=2))
    
    response = requests.post(
        f"{API_URL}/verify-cfdi-batch",
        headers=headers,
        json=test_data
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        # Truncate response for better readability
        response_data = response.json()
        for item in response_data.get("results", []):
            if "response" in item and "raw_response" in item["response"]:
                item["response"]["raw_response"] = item["response"]["raw_response"][:100] + "... (truncated)"
        print("Response (truncated):")
        print(json.dumps(response_data, indent=2))
    else:
        print(f"Error Response: {response.text}")
        
    assert response.status_code == 200
    assert "results" in response.json()
    
def test_check_rfc_efos(headers):
    """Test the check-rfc-efos endpoint"""
    print(f"\nTesting RFC EFOS Check on {API_URL}...")
    
    # Test data for a known RFC in EFOS list
    test_data = {
        "rfc": "AAA100303L51"
    }
    
    print("Request:")
    print(json.dumps(test_data, indent=2))
    
    response = requests.post(
        f"{API_URL}/check-rfc-efos",
        headers=headers,
        json=test_data
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("Response:")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error Response: {response.text}")
        
    assert response.status_code == 200
    assert "rfc" in response.json()
    assert "is_in_efos_list" in response.json()
    
def test_check_rfc_efos_batch(headers):
    """Test the check-rfc-efos-batch endpoint"""
    print(f"\nTesting Batch RFC EFOS Check on {API_URL}...")
    
    # Test data
    test_data = {
        "rfcs": ["AAA100303L51", "AAA120730823", "AAA121206EV5"]
    }
    
    print("Request:")
    print(json.dumps(test_data, indent=2))
    
    response = requests.post(
        f"{API_URL}/check-rfc-efos-batch",
        headers=headers,
        json=test_data
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("Response:")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error Response: {response.text}")
        
    assert response.status_code == 200
    assert "results" in response.json()
    
def test_unauthorized_access():
    """Test unauthorized access to protected endpoint"""
    print(f"\nTesting Unauthorized Access on {API_URL}...")
    
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
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 401
    assert "detail" in response.json()
    assert response.json()["detail"] == "Not authenticated"

if __name__ == "__main__":
    # Allow running as a standalone script
    print(f"Testing Heroku API at {API_URL}")
    print("=" * 50)
    
    headers_value = headers()
    
    test_health_endpoint()
    test_verify_cfdi(headers_value)
    test_verify_cfdi_batch(headers_value)
    test_check_rfc_efos(headers_value)
    test_check_rfc_efos_batch(headers_value)
    test_unauthorized_access()
    
    print("\nTest Summary")
    print("=" * 50)
    print("All tests passed ✅") 