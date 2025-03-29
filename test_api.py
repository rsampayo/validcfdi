import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API URL - replace with your actual URL (localhost for development)
API_URL = "http://localhost:8000"

# Test data
test_data = {
    "uuid": "6128396f-c09b-4ec6-8699-43c5f7e3b230",
    "emisor_rfc": "CDZ050722LA9",
    "receptor_rfc": "XIN06112344A",
    "total": "12000.00"
}

# Batch test data
batch_test_data = {
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

# API Token - using one of the active tokens from the database
API_TOKEN = "01a486cd562799aafbaaab3ac43dc0af7f8aad3dbd4d2a5e080a2621f1959e17"

def test_health_endpoint():
    """Test the health endpoint"""
    response = requests.get(f"{API_URL}/health")
    print("Health Endpoint:")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print("\n" + "-"*50 + "\n")

def test_verify_cfdi_endpoint():
    """Test the verify-cfdi endpoint"""
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{API_URL}/verify-cfdi", 
        headers=headers,
        json=test_data
    )
    
    print("Verify CFDI Endpoint:")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        # Format the response for better readability
        response_data = response.json()
        # If raw_response exists and is too long, truncate it for display
        if "raw_response" in response_data and response_data["raw_response"]:
            response_data["raw_response"] = response_data["raw_response"][:100] + "... (truncated)"
        
        print(f"Response: {json.dumps(response_data, indent=2)}")
    else:
        print(f"Error Response: {response.text}")
    
    print("\n" + "-"*50 + "\n")

def test_verify_cfdi_batch_endpoint():
    """Test the verify-cfdi-batch endpoint"""
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{API_URL}/verify-cfdi-batch", 
        headers=headers,
        json=batch_test_data
    )
    
    print("Verify CFDI Batch Endpoint:")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        # Format the response for better readability
        response_data = response.json()
        
        # Process each result to truncate raw_response for display
        for result in response_data.get("results", []):
            if "response" in result and "raw_response" in result["response"] and result["response"]["raw_response"]:
                result["response"]["raw_response"] = result["response"]["raw_response"][:100] + "... (truncated)"
        
        print(f"Response: {json.dumps(response_data, indent=2)}")
    else:
        print(f"Error Response: {response.text}")
    
    print("\n" + "-"*50 + "\n")

if __name__ == "__main__":
    print("Testing API Endpoints")
    print("-"*50 + "\n")
    
    try:
        # Test health endpoint
        test_health_endpoint()
        
        # Test verify-cfdi endpoint
        test_verify_cfdi_endpoint()
        
        # Test verify-cfdi-batch endpoint
        test_verify_cfdi_batch_endpoint()
        
    except Exception as e:
        print(f"Error testing API: {e}") 