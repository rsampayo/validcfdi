import requests
import json

# API URL - replace with your actual URL (localhost for development)
API_URL = "http://localhost:8000"

# Test data
test_data = {
    "uuid": "6128396f-c09b-4ec6-8699-43c5f7e3b230",
    "emisor_rfc": "CDZ050722LA9",
    "receptor_rfc": "XIN06112344A",
    "total": "12000.00"
}

# API Token - replace with your actual token
API_TOKEN = "your-secret-token"

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

if __name__ == "__main__":
    print("Testing API Endpoints")
    print("-"*50 + "\n")
    
    try:
        # Test health endpoint
        test_health_endpoint()
        
        # Test verify-cfdi endpoint
        test_verify_cfdi_endpoint()
        
    except Exception as e:
        print(f"Error testing API: {e}") 