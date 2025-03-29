import requests
import json
import base64

# API URL - replace with your actual URL (localhost for development)
API_URL = "http://localhost:8001"

# Superadmin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password"

def get_basic_auth_header(username, password):
    """Create HTTP Basic auth header"""
    credentials = f"{username}:{password}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"

def test_create_token():
    """Test creating a new API token"""
    headers = {
        "Authorization": get_basic_auth_header(ADMIN_USERNAME, ADMIN_PASSWORD),
        "Content-Type": "application/json"
    }
    
    data = {
        "description": "Test token"
    }
    
    response = requests.post(
        f"{API_URL}/admin/tokens",
        headers=headers,
        json=data
    )
    
    print("\nCreate Token Endpoint:")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200 or response.status_code == 201:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.json()
    else:
        print(f"Error Response: {response.text}")
        return None

def test_list_tokens():
    """Test listing all API tokens"""
    headers = {
        "Authorization": get_basic_auth_header(ADMIN_USERNAME, ADMIN_PASSWORD)
    }
    
    response = requests.get(
        f"{API_URL}/admin/tokens",
        headers=headers
    )
    
    print("\nList Tokens Endpoint:")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        tokens = response.json()
        # Truncate the output if there are many tokens
        if tokens.get("tokens") and len(tokens["tokens"]) > 3:
            tokens["tokens"] = tokens["tokens"][:3]
            tokens["tokens"].append({"note": "... more tokens truncated ..."})
        print(f"Response: {json.dumps(tokens, indent=2)}")
    else:
        print(f"Error Response: {response.text}")

def test_regenerate_token(token_id):
    """Test regenerating an API token"""
    headers = {
        "Authorization": get_basic_auth_header(ADMIN_USERNAME, ADMIN_PASSWORD)
    }
    
    response = requests.post(
        f"{API_URL}/admin/tokens/{token_id}/regenerate",
        headers=headers
    )
    
    print("\nRegenerate Token Endpoint:")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.json()
    else:
        print(f"Error Response: {response.text}")
        return None

def test_verify_cfdi_with_token(token):
    """Test CFDI verification with a token"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
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
    
    print("\nVerify CFDI with Token:")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        # Format the response for better readability
        response_data = response.json()
        # Truncate raw_response if necessary
        if "raw_response" in response_data and response_data["raw_response"]:
            response_data["raw_response"] = response_data["raw_response"][:100] + "... (truncated)"
        
        print(f"Response: {json.dumps(response_data, indent=2)}")
    else:
        print(f"Error Response: {response.text}")

if __name__ == "__main__":
    print("Testing Admin API Endpoints")
    print("-" * 50)
    
    # List existing tokens
    test_list_tokens()
    
    # Create a new token
    new_token = test_create_token()
    
    if new_token:
        # Test the new token with CFDI verification
        token_value = new_token["token"]
        print(f"\nUsing token: {token_value}")
        test_verify_cfdi_with_token(token_value)
        
        # Regenerate the token
        token_id = new_token["id"]
        regenerated = test_regenerate_token(token_id)
        
        if regenerated:
            # Test with regenerated token
            token_value = regenerated["token"]
            print(f"\nUsing regenerated token: {token_value}")
            test_verify_cfdi_with_token(token_value) 